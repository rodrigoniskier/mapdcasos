import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-only-change-me')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in {'1', 'true', 'yes', 'on'}
APP_ENV = os.getenv('APP_ENV', 'development' if DEBUG else 'production')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.pythonanywhere.com').split(',') if h.strip()]
CSRF_TRUSTED_ORIGINS = ['https://*.pythonanywhere.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.observability.RequestIdMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=int(os.getenv('DB_CONN_MAX_AGE', '60')),
            conn_health_checks=True,
            ssl_require=False,
        )
    }
else:
    # SQLite is kept only as a low-load/bootstrap fallback. Production with a
    # simultaneous class should set DATABASE_URL to PostgreSQL.
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {'timeout': 20},
        }
    }

# Shared cache is used by rate limiting and circuit breakers. Redis is preferred
# with multiple workers; the file cache keeps local/test deployments functional.
REDIS_URL = os.getenv('REDIS_URL', '').strip()
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'TIMEOUT': 300,
            'KEY_PREFIX': 'mapdcasos',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': str(BASE_DIR / '.django-cache'),
            'TIMEOUT': 300,
            'OPTIONS': {'MAX_ENTRIES': 5000},
            'KEY_PREFIX': 'mapdcasos',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Fortaleza'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'core.User'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

# Signed-cookie sessions are stateless across web workers and remove session-table
# writes from the hot path. Only small authentication/session metadata is stored.
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', '28800'))
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', 'True' if not DEBUG else 'False').lower() in {'1', 'true', 'yes', 'on'}
SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0

# RN AI Gateway -------------------------------------------------------------
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY', '')
GEMINI_API_VERSION = os.getenv('GEMINI_API_VERSION', 'v1')
GEMINI_CHAT_MODEL = os.getenv('GEMINI_CHAT_MODEL', 'gemini-3.5-flash-lite')
GEMINI_CHAT_FALLBACK_MODEL = os.getenv('GEMINI_CHAT_FALLBACK_MODEL', 'gemini-3.6-flash')
GEMINI_EVALUATION_MODEL = os.getenv('GEMINI_EVALUATION_MODEL', os.getenv('GEMINI_MODEL', 'gemini-3.6-flash'))
GEMINI_EVALUATION_FALLBACK_MODEL = os.getenv('GEMINI_EVALUATION_FALLBACK_MODEL', 'gemini-3.5-flash-lite')
GEMINI_RETRY_ATTEMPTS = max(1, int(os.getenv('GEMINI_RETRY_ATTEMPTS', '3')))
GEMINI_HTTP_TIMEOUT_MS = max(3000, int(os.getenv('GEMINI_HTTP_TIMEOUT_MS', '15000')))
GEMINI_CHAT_MAX_OUTPUT_TOKENS = max(128, int(os.getenv('GEMINI_CHAT_MAX_OUTPUT_TOKENS', '512')))
GEMINI_EVALUATION_MAX_OUTPUT_TOKENS = max(512, int(os.getenv('GEMINI_EVALUATION_MAX_OUTPUT_TOKENS', '1800')))
GEMINI_CHAT_THINKING_LEVEL = os.getenv('GEMINI_CHAT_THINKING_LEVEL', 'minimal')
GEMINI_EVALUATION_THINKING_LEVEL = os.getenv('GEMINI_EVALUATION_THINKING_LEVEL', 'medium')
GEMINI_FALLBACK_ON_QUOTA = os.getenv('GEMINI_FALLBACK_ON_QUOTA', 'True').lower() in {'1', 'true', 'yes', 'on'}
GEMINI_CIRCUIT_FAILURE_THRESHOLD = max(2, int(os.getenv('GEMINI_CIRCUIT_FAILURE_THRESHOLD', '5')))
GEMINI_CIRCUIT_COOLDOWN_SECONDS = max(10, int(os.getenv('GEMINI_CIRCUIT_COOLDOWN_SECONDS', '45')))

AI_ENABLED = os.getenv('AI_ENABLED', 'True').lower() in {'1', 'true', 'yes', 'on'}
PATIENT_AI_ENABLED = os.getenv('PATIENT_AI_ENABLED', 'True').lower() in {'1', 'true', 'yes', 'on'}
EVALUATION_AI_ENABLED = os.getenv('EVALUATION_AI_ENABLED', 'True').lower() in {'1', 'true', 'yes', 'on'}
AI_BACKGROUND_ENABLED = os.getenv('AI_BACKGROUND_ENABLED', 'True').lower() in {'1', 'true', 'yes', 'on'}
AI_SCHEMA_REPAIR_ATTEMPTS = max(0, int(os.getenv('AI_SCHEMA_REPAIR_ATTEMPTS', '1')))
AI_JOB_MAX_WAIT_SECONDS = max(15, int(os.getenv('AI_JOB_MAX_WAIT_SECONDS', '75')))
AI_MAX_PENDING_PER_USER = max(1, int(os.getenv('AI_MAX_PENDING_PER_USER', '2')))
AI_MAX_PENDING_GLOBAL = max(5, int(os.getenv('AI_MAX_PENDING_GLOBAL', '60')))
AI_RATE_LIMIT_USER_PER_MINUTE = max(1, int(os.getenv('AI_RATE_LIMIT_USER_PER_MINUTE', '15')))
AI_RATE_LIMIT_GLOBAL_PER_MINUTE = max(10, int(os.getenv('AI_RATE_LIMIT_GLOBAL_PER_MINUTE', '240')))
AI_RATE_LIMIT_KIND_PER_MINUTE = max(10, int(os.getenv('AI_RATE_LIMIT_KIND_PER_MINUTE', '180')))
AI_MAX_USER_MESSAGE_CHARS = max(500, int(os.getenv('AI_MAX_USER_MESSAGE_CHARS', '2500')))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'rn': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'rn',
        },
    },
    'loggers': {
        'core': {
            'handlers': ['console'],
            'level': os.getenv('APP_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}
