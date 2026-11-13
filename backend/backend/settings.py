"""
Django settings for backend project (Django 5.2 LTS, Python 3.12).

Lines marked  # DISABLED  were commented out (not deleted) because they depend on
packages or apps that are not in the new base.txt. Uncomment them later if needed.
"""

import os
import sys
from pathlib import Path
from corsheaders.defaults import default_headers
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(os.path.join(BASE_DIR, "backend/apps/"))

SECRET_KEY = os.getenv("SECRET_KEY")

# Env
ENV = os.getenv("ENV")
IS_DEV = ENV == "dev"
IS_STAGE = ENV == "stage"
IS_PROD = ENV == "prod"

# Email
DEFAULT_FROM_EMAIL = "BackWater Resources Pvt Ltd <noreply@backwaterglobal.com>"

# FIXED: these were only defined when IS_DEV, so any other ENV crashed on WWW_ROOT.
DOMAIN_NAME = os.getenv("DOMAIN_NAME", "localhost:80")
PROTOCOl_NAME = "http" if IS_DEV else "https"

# FIXED: DEBUG was undefined outside dev/stage.
DEBUG = IS_DEV or IS_STAGE

WWW_ROOT = f"{PROTOCOl_NAME}://{DOMAIN_NAME}"

ALLOWED_HOSTS = ["*"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 'django.contrib.sites',          # DISABLED: only allauth needed it (SITE_ID below)
    "rest_framework",
    "rest_framework.authtoken",  # temporary, until cookie JWT login is added
    "corsheaders",
    "django_filters",
    "accounts",
    "common",
    "inquiries",
    "dashboard",
    "reports",
    "notifications",
    "import_export",
    # keep: holds common.storage
    # 'product',                       # DISABLED: old project app (uses old User fields)
    # 'company',                       # DISABLED: old project app
    "drf_spectacular",
    # 'ERPintegration',                # DISABLED: old project app
    # Google auth, DISABLED: packages removed from base.txt
    # 'allauth',
    # 'allauth.account',
    # 'allauth.socialaccount',
    # 'allauth.socialaccount.providers.google',
    # 'oauth2_provider',
    # 'social_django',
    # 'drf_social_oauth2',
    # 'import_export',                 # DISABLED: django-import-export is optional in base.txt
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # FIXED: CorsMiddleware must come before CommonMiddleware (it was last).
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # 'allauth.account.middleware.AccountMiddleware',   # DISABLED: re-add with allauth
]

ROOT_URLCONF = "backend.urls"

AUTH_USER_MODEL = "accounts.User"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": f"{os.getenv('POSTGRES_DB')}",
        "USER": f"{os.getenv('POSTGRES_USER')}",
        "PASSWORD": f"{os.getenv('POSTGRES_PASSWORD')}",
        "HOST": f"{os.getenv('POSTGRES_HOST')}",
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
# USE_L10N = True                      # REMOVED in Django 5.0 (always on)
USE_TZ = True

# Static / media
FILE_UPLOAD_MAX_MEMORY_SIZE = 4194304  # 4mb

STATIC_URL = "/static/"
STATICFILES_LOCATION = "static"
MEDIA_URL = "/uploads/"

# CHANGED: STATICFILES_STORAGE / DEFAULT_FILE_STORAGE were removed in Django 5.1.
STORAGES = {
    "default": {"BACKEND": "common.storage.S3MediaStorage"},
    "staticfiles": {"BACKEND": "common.storage.StaticS3Boto3Storage"},
}

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")

AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_URL")
MINIO_ACCESS_URL = os.getenv("MINIO_ACCESS_URL")
AWS_S3_URL_PROTOCOL = "http:"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS
# CHANGED: old names (CORS_ORIGIN_ALLOW_ALL / CORS_ORIGIN_WHITELIST) were removed
# in django-cors-headers 4.x.
CORS_ALLOW_ALL_ORIGINS = IS_DEV
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:80",
    "http://0.0.0.0:80",
]
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOW_HEADERS = default_headers


# simple jwt for artisera
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=36500),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=36500),
}


"""
# old chabson auth
# FIXED: REST_FRAMEWORK was defined twice (the second silently replaced the first,
# so IsAuthenticated was never applied). Now a single dict.
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',   # temporary
        # 'oauth2_provider.contrib.rest_framework.OAuth2Authentication',  # DISABLED
        # 'drf_social_oauth2.authentication.SocialAuthentication',        # DISABLED
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # TODO: replace with the custom {count, page, pageSize, results} pagination class
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 6,
}

"""

# celery configurations
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    # DISABLED: Google / social login
    # 'allauth.account.auth_backends.AuthenticationBackend',
    # 'accounts.auth_backends.PhoneOTPBackend',   # old accounts module, not in new accounts app
    # 'social_core.backends.google.GoogleOAuth2',
    # 'drf_social_oauth2.backends.DjangoOAuth2',
]

# DISABLED: Google auth settings (restore together with the packages above)
# SOCIALACCOUNT_PROVIDERS = {
#     'google': {
#         'SCOPE': ['profile', 'email'],
#         'AUTH_PARAMS': {'access_type': 'online'},
#     }
# }
# SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY")
# SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET")
# SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
#     'https://www.googleapis.com/auth/userinfo.email',
#     'https://www.googleapis.com/auth/userinfo.profile',
# ]
# SITE_ID = 5

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Email
# CHANGED: sendgrid_backend is not in base.txt; console output in dev, SMTP/sendgrid later.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# DISABLED: re-enable after adding django-sendgrid-v5 to base.txt
# EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
# SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
# SENDGRID_SANDBOX_MODE_IN_DEBUG = False
# SENDGRID_ECHO_TO_STDOUT = True
