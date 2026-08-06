"""
Django settings for the forkcast project.

Stack: see docs/03-tech-stack.md at the project root.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-do-not-use-in-production",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]
if DEBUG:
    ALLOWED_HOSTS += ["localhost", "127.0.0.1"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "storages",
    "recipes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "forkcast.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "forkcast.wsgi.application"


# Database
# Locally, no DATABASE_URL is set -> SQLite (zero setup).
# In production, DATABASE_URL points to Supabase (PostgreSQL) -- see docs/03-tech-stack.md.

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# French-speaking household (Québec) -- see docs/01-requirements.md. The codebase and docs are in
# English, but the UI stays in French since that's the household's language.

LANGUAGE_CODE = "fr-ca"

TIME_ZONE = "America/Toronto"

USE_I18N = True

USE_TZ = True


# Static & media files

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Recipe photo storage: local filesystem by default (zero setup). Set SUPABASE_STORAGE_BUCKET
# (and the other SUPABASE_STORAGE_* vars below) to switch to Supabase Storage instead -- see
# .env.example and docs/03-tech-stack.md.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET")

if SUPABASE_STORAGE_BUCKET:
    SUPABASE_PROJECT_REF = os.environ["SUPABASE_PROJECT_REF"]
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": SUPABASE_STORAGE_BUCKET,
                "endpoint_url": f"https://{SUPABASE_PROJECT_REF}.supabase.co/storage/v1/s3",
                "region_name": os.environ.get("SUPABASE_STORAGE_REGION", "us-east-1"),
                "access_key": os.environ["SUPABASE_STORAGE_ACCESS_KEY_ID"],
                "secret_key": os.environ["SUPABASE_STORAGE_SECRET_ACCESS_KEY"],
                # Supabase serves public objects from its own REST path, not the S3 endpoint
                # above (that one is for authenticated S3-API access, uploads included) --
                # custom_domain overrides how django-storages builds the public .url() so
                # <img src> tags get a URL that's actually readable anonymously.
                "custom_domain": (
                    f"{SUPABASE_PROJECT_REF}.supabase.co/storage/v1/object/public/"
                    f"{SUPABASE_STORAGE_BUCKET}"
                ),
                "default_acl": None,
                "querystring_auth": False,
                "file_overwrite": False,
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "recipes:login"
LOGIN_REDIRECT_URL = "recipes:list"
LOGOUT_REDIRECT_URL = "recipes:login"
