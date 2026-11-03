"""
Django settings for the Muhammad Nouman portfolio.

Everything environment-specific comes from `.env` (see `.env.example`).
Defaults are safe for production: DEBUG is off unless you turn it on.
"""
import secrets
from pathlib import Path

from decouple import config, Csv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------
# Core / security
# ------------------------------------------------------------------
DEBUG = config('DEBUG', default=False, cast=bool)

SECRET_KEY = config('SECRET_KEY', default='')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-' + secrets.token_urlsafe(32)
    else:
        raise ImproperlyConfigured(
            'SECRET_KEY is not set. Generate one with: '
            'python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"'
        )

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())
# Public origin of the site, no trailing slash. Used for canonical URLs, sitemap and Open Graph.
SITE_URL = config('SITE_URL', default='http://127.0.0.1:8000').rstrip('/')
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default=SITE_URL if SITE_URL.startswith('https') else '', cast=Csv())

SITE_NAME = config('SITE_NAME', default='Muhammad Nouman')

# Private dashboard lives here (no leading slash, trailing slash required). Change it to hide it.
DASHBOARD_URL = config('DASHBOARD_URL', default='dashboard/')
# The stock Django admin is switched off unless you ask for it.
ENABLE_DJANGO_ADMIN = config('ENABLE_DJANGO_ADMIN', default=False, cast=bool)
DJANGO_ADMIN_URL = config('DJANGO_ADMIN_URL', default='django-admin/')

# ------------------------------------------------------------------
# Applications
# ------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'apps.siteconfig',
    'apps.home',
    'apps.about',
    'apps.experience',
    'apps.projects',
    'apps.blog',
    'apps.services',
    'apps.skills',
    'apps.contact',
    'apps.analytics',
    'apps.dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.analytics.middleware.VisitorTrackingMiddleware',
]

# WhiteNoise serves compressed, fingerprinted static files straight from gunicorn.
# It is optional so the project still runs before `pip install -r requirements.txt` finishes.
try:  # pragma: no cover
    import whitenoise  # noqa: F401
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    _HAS_WHITENOISE = True
except ImportError:  # pragma: no cover
    _HAS_WHITENOISE = False

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_meta',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------
_db_engine = config('DB_ENGINE', default='django.db.backends.sqlite3')

if 'sqlite3' in _db_engine:
    DATABASES = {
        'default': {
            'ENGINE': _db_engine,
            'NAME': BASE_DIR / config('DB_NAME', default='db.sqlite3'),
            'OPTIONS': {'timeout': 20},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': _db_engine,
            'NAME': config('DB_NAME', default='nouman_portfolio'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='127.0.0.1'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 60,
        }
    }

CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'portfolio'}}

# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LOGIN_URL = f'/{DASHBOARD_URL}login/'
LOGIN_REDIRECT_URL = f'/{DASHBOARD_URL}'
LOGOUT_REDIRECT_URL = '/'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# ------------------------------------------------------------------
# I18N
# ------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = config('TIME_ZONE', default='Asia/Karachi')
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------
# Static & media
# ------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
            if (_HAS_WHITENOISE and not DEBUG)
            else 'django.contrib.staticfiles.storage.StaticFilesStorage'
        )
    },
}
DATA_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ------------------------------------------------------------------
# Behind a reverse proxy (nginx, Cloudflare, Caddy ...)
# ------------------------------------------------------------------
BEHIND_PROXY = config('BEHIND_PROXY', default=False, cast=bool)
if BEHIND_PROXY:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True

# ------------------------------------------------------------------
# HTTPS hardening (only when DEBUG is off)
# ------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
    SESSION_COOKIE_SECURE = SITE_URL.startswith('https')
    CSRF_COOKIE_SECURE = SITE_URL.startswith('https')
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000 if SITE_URL.startswith('https') else 0, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
    SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# ------------------------------------------------------------------
# Email (optional: contact-form notifications to the owner)
# ------------------------------------------------------------------
EMAIL_HOST = config('EMAIL_HOST', default='')
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Portfolio <no-reply@localhost>')

# ------------------------------------------------------------------
# Visitor analytics (see apps/analytics)
# ------------------------------------------------------------------
ANALYTICS_ENABLED = config('ANALYTICS_ENABLED', default=True, cast=bool)
ANALYTICS_TRACK_STAFF = config('ANALYTICS_TRACK_STAFF', default=False, cast=bool)
ANALYTICS_USE_COOKIE = config('ANALYTICS_USE_COOKIE', default=True, cast=bool)
ANALYTICS_ANONYMIZE_IP = config('ANALYTICS_ANONYMIZE_IP', default=False, cast=bool)
ANALYTICS_RETENTION_DAYS = config('ANALYTICS_RETENTION_DAYS', default=400, cast=int)
# Trust X-Forwarded-For / CF-Connecting-IP for the visitor IP. Only enable behind your own proxy.
ANALYTICS_TRUST_PROXY_HEADERS = config('ANALYTICS_TRUST_PROXY_HEADERS', default=BEHIND_PROXY, cast=bool)
# Optional MaxMind GeoLite2 folder (needs `pip install geoip2`). Country also works from CDN headers.
GEOIP_PATH = config('GEOIP_PATH', default='')

# ------------------------------------------------------------------
# Owner info: first-run defaults for the Site settings page in the dashboard
# ------------------------------------------------------------------
OWNER_NAME = config('OWNER_NAME', default='Muhammad Nouman')
OWNER_EMAIL = config('OWNER_EMAIL', default='nomannisar769@gmail.com')
OWNER_PHONE = config('OWNER_PHONE', default='0324 8699647')
OWNER_LOCATION = config('OWNER_LOCATION', default='Sheikhupura, Pakistan')
OWNER_GITHUB = config('OWNER_GITHUB', default='https://github.com/MuhammadNouman769')
OWNER_LINKEDIN = config('OWNER_LINKEDIN', default='https://www.linkedin.com/in/muhammad-nouman-524ab9360/')

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'plain': {'format': '%(asctime)s %(levelname)s %(name)s: %(message)s'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False}},
}
