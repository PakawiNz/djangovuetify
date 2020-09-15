import environ

from utils.format_utils import camel

root = environ.Path(__file__) - 2
env = environ.Env()
env.read_env(root('.env'))

BASE_DIR = root()

SECRET_KEY = env('SECRET_KEY')

DEBUG = env('DEBUG', default=False)

if DEBUG:
    import socket

    ALLOWED_HOSTS = ['localhost', '127.0.0.1', socket.gethostbyname(socket.gethostname()), ]
else:
    ALLOWED_HOSTS = env('ALLOWED_HOST')

# ================================================== APPLICATIONS

PLATFORM_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'rest_framework',
    'channels',
    'utils.admin_utils.CommonAdminConfig',
    'core.apps.CoreConfig',
]

USER_APPS = [
]

INSTALLED_APPS = PLATFORM_APPS + [f'apps.{app}.apps.{camel(app)}Config' for app in USER_APPS]

ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.wsgi.application'

# ================================================== MIDDLEWARE

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ================================================== DATABASE

if env('ENABLE_POSTGRES', cast=bool, default=False):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'postgres',
            'USER': 'postgres',
            'HOST': 'db',  # set in docker-compose.yml
            'PORT': 5432  # default postgres port
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'db.sqlite3',
        }
    }

# ================================================== PASSWORD VALIDATORS

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

# ================================================== INTERNATIONALIZATION

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Bangkok'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# ================================================== TEMPLATES

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates', root('vue', 'dist')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ================================================== STATICFILES

STATIC_URL = '/static/'

STATIC_ROOT = root('static')

STATICFILES_DIRS = [
    root('vue', 'dist'),
]

# ================================================== STORAGE

STORAGE_ROOT = root('storage')

# ================================================== CELERY

CELERY_BROKER_URL = 'redis://'
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TIME_ZONE = TIME_ZONE

# ================================================== REST_FRAMEWORK

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    )
}

# ================================================== CHANNEL

ASGI_APPLICATION = 'config.routing.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('redis', 6379)],
        },
    },
}
