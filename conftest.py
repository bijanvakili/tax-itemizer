import os

from django.db import connections
import dj_database_url
import pytest
import testing.postgresql


TESTING_POSTGRESQL_KEEP_DB_PATH = '.testdb'


@pytest.fixture(scope='session')
def django_db_modify_db_settings(django_db_keepdb):
    from django.conf import settings

    testdb_kwargs = {}
    if django_db_keepdb:
        testdb_kwargs['base_dir'] = os.path.join(os.getcwd(), TESTING_POSTGRESQL_KEEP_DB_PATH)

    with testing.postgresql.Postgresql(**testdb_kwargs) as postgresql:
        db_url = postgresql.url()

        settings.DATABASES['default'] = dj_database_url.parse(db_url)
        settings.DATABASES['default']['TEST'] = {
            'NAME': settings.DATABASES['default']['NAME']
        }

        yield

        for connection in connections.all():
            connection.close()
