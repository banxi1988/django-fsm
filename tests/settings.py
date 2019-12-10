import django

PROJECT_APPS = ('django_fsm_ex', 'tests.testapp',)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'guardian',
) + PROJECT_APPS

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend', # this is default
    'guardian.backends.ObjectPermissionBackend',
)

DATABASE_ENGINE = 'sqlite3'
SECRET_KEY = 'nokey'
MIDDLEWARE_CLASSES = ()
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

MIGRATION_MODULES = {
'auth': None,
'contenttypes': None,
'guardian': None,
}


ANONYMOUS_USER_ID = 0
AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend', 'guardian.backends.ObjectPermissionBackend')