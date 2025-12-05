import os
import structlog
import sys

from corsheaders.defaults import default_headers
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'var/log')
# LOG_DIR = os.path.join(BASE_DIR, '/var/log/django')
CACHE_DIR = os.path.join(BASE_DIR, 'var/cache')

if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)

if not os.path.exists(CACHE_DIR):
    os.mkdir(CACHE_DIR)

# Load Environment variables, defaulting to prod, where
# we don't inject DJANGO_ENV.
DJANGO_ENV = os.getenv("DJANGO_ENV", "prod")
ENVIRONMENTS = {
  "local": ".env.local",
  "docker": ".env.docker",
}

sys.stdout.write(f"Loading environment {DJANGO_ENV}\n")
dotenv_path = os.path.join(BASE_DIR, "config", ENVIRONMENTS.get(DJANGO_ENV) or ".env")

sys.stdout.write(f"Loading environment variables from {dotenv_path}\n")
load_dotenv(dotenv_path)

# Secrets
SECRET_KEY = os.getenv("SECRET_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Other common settings that vary by environment
allowed_hosts = os.getenv("ALLOWED_HOSTS")
if allowed_hosts is not None:
  ALLOWED_HOSTS = list(allowed_hosts.split(","))

trusted_origins = os.getenv("CSRF_TRUSTED_ORIGINS")
if trusted_origins is not None:
  CSRF_TRUSTED_ORIGINS = list(trusted_origins.split(","))

allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS")
if allowed_origins is not None:
  CORS_ALLOWED_ORIGINS = list(allowed_origins.split(","))

CORS_ALLOW_HEADERS = (
    *default_headers,
    "x-correlation-id",
)

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() == "true"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() == "true"
CORS_ALLOW_CREDENTIALS = True

ADMIN_URL = os.getenv("ADMIN_URL")
WEBSITE_URL = os.getenv("WEBSITE_URL")

# Common settings
SITE_ID = 1

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

ROOT_URLCONF = "bhmc.urls"

WSGI_APPLICATION = "bhmc.wsgi.application"

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Chicago"

USE_I18N = False

USE_L10N = False

USE_TZ = True

INSTALLED_APPS = (
    "anymail",
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
    "django.contrib.contenttypes",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.humanize",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django_structlog",
    "djoser",
    "imagekit",
    "pagedown.apps.PagedownConfig",
    "rest_framework",
    "rest_framework.authtoken",
    "storages",
    "content",
    "core",
    "courses",
    "damcup",
    "documents",
    "events",
    "messaging",
    "payments",
    "policies",
    "register",
    "reporting",
    "scores",
)

MIDDLEWARE = (
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.RemoteUserMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
    "core.middleware.auth_token",
)

AUTHENTICATION_BACKENDS = [
    "djoser.auth_backends.LoginFieldBackend",
    "django.contrib.auth.backends.ModelBackend",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates"), ],
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

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
    ),
    "EXCEPTION_HANDLER": "core.exception_handler.custom_exception_handler",
}

DJOSER = {
    "PASSWORD_RESET_CONFIRM_URL": "session/reset-password/{uid}/{token}",
    "ACTIVATION_URL": "session/account/activate/{uid}/{token}",
    "SEND_ACTIVATION_EMAIL": True,
    "PASSWORD_RESET_CONFIRM_RETYPE": True,
    "LOGIN_FIELD": "email",
    "DEFAULT_FROM_EMAIL": "postmaster@bhmc.org",
    "SERIALIZERS": {
        "current_user": "core.serializers.UserDetailSerializer",
        "user_create": "core.serializers.UserCreateSerializer",
    },
    "EMAIL": {
        "activation": "core.email.ActivationEmail",
        "password_reset": "core.email.PasswordResetEmail",
    }
}
LOGIN_REDIRECT_URL = "/"

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json_formatter": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
        },
        "plain_console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(),
        },
        "key_value": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.KeyValueRenderer(key_order=['timestamp', 'level', 'event', 'logger']),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "plain_console",
        },
        "flat_line_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": LOG_DIR + "/bhmc.log",
            "when": "W5",
            "backupCount": 12,
            "formatter": "key_value",
        },
        "celery_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": LOG_DIR + "/celery.log",
            "when": "W5",
            "backupCount": 12,
            "formatter": "key_value",
        },
    },
    "loggers": {
        "django_structlog": {
            "handlers": ["console", "flat_line_file"],
            "level": "ERROR",
        },
        "celery": {
            "handlers": ["console", "celery_file"],
            "level": "INFO",
        },
        "stripe": {
            "handlers": ["console", "flat_line_file"] ,
            "level": "ERROR",
        },
        "core": {
            "handlers": ["console", "flat_line_file"],
            "level": "INFO",
        },
        "damcup": {
            "handlers": ["console", "flat_line_file"],
            "level": "INFO",
        },
        "payments": {
            "handlers": ["console", "flat_line_file"],
            "level": "INFO",
        },
        "register": {
            "handlers": ["console", "flat_line_file"],
            "level": "INFO",
        },
        "scores": {
            "handlers": ["console", "flat_line_file"],
            "level": "INFO",
        },
    }
}

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

DJANGO_STRUCTLOG_CELERY_ENABLED = True

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv("DATABASE_NAME"),
        'USER': os.getenv("DATABASE_USER"),
        'PASSWORD': os.getenv("DATABASE_PASSWORD"),
        'HOST': os.getenv("DATABASE_HOST"),
        'PORT': os.getenv("DATABASE_PORT"),
    }
}

# Caching
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL"),
    },
    "file": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": CACHE_DIR,
    }
}

# Celery
CELERY_BROKER_URL = os.getenv("REDIS_URL")
CELERY_RESULT_BACKEND = "django-db"
CELERY_TIMEZONE = "America/Chicago"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TRACK_STARTED = True

# Storage
AWS_HEADERS = {
    'Expires': 'Thu, 31 Dec 2099 20:00:00 GMT',
    'Cache-Control': 'max-age=94608000',
}
AWS_S3_FILE_OVERWRITE = True
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME

STATICFILES_LOCATION = 'static'
MEDIAFILES_LOCATION = 'media'

STATIC_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, STATICFILES_LOCATION)
MEDIA_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, MEDIAFILES_LOCATION)

STORAGES = {
    "default": {
        "BACKEND": "custom_storages.MediaStorage",
    },
    "staticfiles": {
        "BACKEND": "custom_storages.StaticStorage",
    },
}

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Email settings
ADMINS = [('Stuart Finley', 'finleysg@gmail.com')]
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND")

if DJANGO_ENV == "prod":
    ANYMAIL = {
        "MAILGUN_API_KEY": os.getenv("MAILGUN_API_KEY"),
        "MAILGUN_SENDER_DOMAIN": "bhmc.org",
    }
    DEFAULT_FROM_EMAIL = "postmaster@bhmc.org"
elif DJANGO_ENV == "docker":
    EMAIL_HOST = "mail"
    EMAIL_PORT = 1025
    EMAIL_USE_TLS = False
    EMAIL_USE_SSL = False
else:
    EMAIL_HOST = "smtp.mailtrap.io"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
    EMAIL_PORT = 2525
    EMAIL_USE_TLS = True
    EMAIL_USE_SSL = False
