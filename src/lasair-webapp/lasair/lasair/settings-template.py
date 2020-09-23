"""
Django settings for lasair project.
"""

DEFAULT_FROM_EMAIL = "donotreply@roe.ac.uk"
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'localhost'
#EMAIL_HOST = 'smtp.roe.ac.uk'
EMAIL_PORT = 25 

LASAIR_ROOT = '/home/roy/'

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases
DEBUG          = True
WEB_DOMAIN     = 'lasair-iris'
READONLY_USER  = ''
READONLY_PASS  = ''

READWRITE_USER = 'f'
READWRITE_PASS = '7'

DB_HOST        = ''

DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ''

QUERY_CACHE = LASAIR_ROOT + 'query_cache'

CITIZEN_SCIENCE_USERID = 0
CITIZEN_SCIENCE_KEY    = ''

BLOB_STORE_ROOT = '/blah/blah'
################################################################
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_ROOT = os.path.join(BASE_DIR, "static")

ALLOWED_HOSTS = ["*"]

# Application definition

# 2020-07-07 KWS Added lasairapi, rest_framework and rest_framework.authtoken.
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'lasair',
    'lasairapi',
    'django.contrib.admin',
    'rest_framework',
    'rest_framework.authtoken',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 2020-07-07 KWS Added token authentication class
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.UserRateThrottle',
     ),
     'DEFAULT_THROTTLE_RATES': {
         'user': '10/hour',
     },
}

ROOT_URLCONF = 'lasair.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['./templates',],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'lasair.context-processors.dev',
            ],
        },
    },
]

WSGI_APPLICATION = 'lasair.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql', 
        'NAME':     'ztf',
        'USER':     READWRITE_USER,
        'PASSWORD': READWRITE_PASS,
        'HOST':     DB_HOST, 
    }
}

CASSANDRA = {
    'default': {
        'KEYSPACE': CASSANDRA_KEYSPACE,
        'USER':     CASSANDRA_USER,
        'PASSWORD': CASSANDRA_PASS,
        'HOSTS':    CASSANDRA_HOSTS,
    }
}


# Redirect to home URL after login (Default redirects to /accounts/profile/)
LOGIN_REDIRECT_URL = '/'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/lasair/static/"

# 2020-08-18 KWS Moved our local static files to a directory called "staticfiles".
STATICFILES_DIRS = (
  os.path.join(BASE_DIR, 'staticfiles'),
)
