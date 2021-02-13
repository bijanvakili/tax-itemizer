#!/bin/bash
set -e

export ROOT_PATH=`pwd`
export PYTHONPATH="${ROOT_PATH}"

COMMAND="$1"
if [ -z ${COMMAND} ]; then
    (>&2 echo 'No command specified')
    exit 2
fi

# force test and lint commands to always use 'test' environment
if [ "${COMMAND}" == "test" ] || [ "${COMMAND}" == "lint" ]; then
    export RECEIPTS_ENV=test
fi

if [ -z ${RECEIPTS_ENV} ]; then
    (>&2 echo 'RECEIPTS_ENV must be specified for non-test commands')
    exit 2
fi

if [ "${COMMAND}" == "test" ]; then
    shift
    RECEIPTS_ENV=test pytest $@
elif [ "${COMMAND}" == "lint" ]; then
    SOURCE_FOLDERS="taxes/"
    flake8 $SOURCE_FOLDERS
    pylint $SOURCE_FOLDERS
    black --check $SOURCE_FOLDERS
elif [ "${COMMAND}" == "web" ]; then
    python manage.py runserver --insecure
else
    python manage.py $@
fi
