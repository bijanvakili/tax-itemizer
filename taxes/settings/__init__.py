"""
Main settings package
"""
import dj_database_url

from taxes.settings.base import *  # noqa: F403  # pylint: disable=wildcard-import
from taxes.receipts.util import yaml

# determine environment name
RECEIPTS_ENV = os.environ.get('RECEIPTS_ENV', None)  # noqa: F405
if not RECEIPTS_ENV:
    raise ValueError('Must specify receipts env')

# load file config
DEFAULT_CONFIG_DIR = os.path.join(os.getcwd(), 'config')  # noqa: F405
RECEIPTS_CONFIG_DIR = os.environ.get('RECEIPTS_CONFIG_DIR', DEFAULT_CONFIG_DIR)  # noqa: F405
RECEIPTS_CONFIG_PATH = os.path.join(  # noqa: F405
    RECEIPTS_CONFIG_DIR,
    f'config.{RECEIPTS_ENV}.yaml'
)

TEST_DATA_FIXTURE_DIR = os.path.join(os.getcwd(), 'data', 'fixtures', 'tests')  # noqa: F405

with open(RECEIPTS_CONFIG_PATH, 'r') as receipt_config_file:
    RECEIPTS_CONFIG = yaml.load(receipt_config_file)

# TODO find out why DEBUG = False is crashing the admin panel
#
# DEBUG = RECEIPTS_CONFIG.get('DEBUG', False)
#
DEBUG = True

LOGGING = RECEIPTS_CONFIG.get('LOGGING')
EXCLUSION_FILTER_MODULES = RECEIPTS_CONFIG.get('EXCLUSION_FILTER_MODULES', [])

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {}
}
if RECEIPTS_ENV == 'test':
    # put the bare minimum so that Django doesn't crash prior to pytest initialization
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'TEST': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2'
        }
    }
else:
    DATABASES['default'] = dj_database_url.parse(RECEIPTS_CONFIG['DATABASE_URI'])

SPREADSHEET = RECEIPTS_CONFIG.get('SPREADSHEET')
