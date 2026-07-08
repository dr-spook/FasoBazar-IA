"""
FasoBazar IA — Django Settings
Stack : Django + SQLite + Bootstrap CDN
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-prod')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Apps FasoBazar
    'apps.core',
    'apps.api',
    'apps.webhook',
    'apps.dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Sert les fichiers statiques en prod
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fasobazar.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'fasobazar.wsgi.application'

# ─── Base de données — SQLite en dev, PostgreSQL en prod ───────────────────
DATABASE_URL = os.getenv('DATABASE_URL', '')

if DATABASE_URL and DATABASE_URL.startswith('postgres'):
    # Production Render — PostgreSQL gratuit
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True)
    }
else:
    # Développement local — SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Ouagadougou'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ─── Sécurité HTTPS (activé uniquement en production) ──────────────────────
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER     = True
    SECURE_CONTENT_TYPE_NOSNIFF   = True
    X_FRAME_OPTIONS                = 'DENY'
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD             = True
    SECURE_SSL_REDIRECT            = True
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True
    # Faire confiance au proxy Render
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Taille max upload audio (25 Mo pour Groq Whisper)
DATA_UPLOAD_MAX_MEMORY_SIZE = 26_214_400
FILE_UPLOAD_MAX_MEMORY_SIZE = 26_214_400

# ─── Clés API ──────────────────────────────────────────────────────────────
GROQ_API_KEY    = os.getenv('GROQ_API_KEY', '')
GEMINI_API_KEY  = os.getenv('GEMINI_API_KEY', '')

TWILIO_ACCOUNT_SID      = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN       = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_NUMBER  = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

DEMO_IMF_TOKEN = os.getenv('DEMO_IMF_TOKEN', 'demo-imf-token-2026')

# ─── Mode Oz ───────────────────────────────────────────────────────────────
OZ_SCENARIO = {
    'product':    os.getenv('OZ_PRODUCT', 'Pagnes bazin'),
    'amount':     int(os.getenv('OZ_AMOUNT', '15000')),
    'type':       os.getenv('OZ_TYPE', 'VENTE'),
    'transcript': "J'ai vendu 3 pagnes bazin à 5 000 francs chacun",
}

# ─── Logging minimal ───────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# ─── Sessions ──────────────────────────────────────────────────────────────
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_NAME    = 'fasobazar_session'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# ─── Auth Trader ───────────────────────────────────────────────────────────
INSTALLED_APPS += ['apps.auth_trader']