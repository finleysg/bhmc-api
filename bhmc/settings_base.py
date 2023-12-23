import os
import structlog


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_DIR = os.path.join(BASE_DIR, 'var/log')
FLAT_LOG_FILE = '/bhmc.log'
FLAT_LOG_PATH = LOG_DIR + FLAT_LOG_FILE

if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)

if not os.path.exists(FLAT_LOG_PATH):
    f = open(FLAT_LOG_PATH, "a").close()
else:
    f = open(FLAT_LOG_PATH, "w").close()

SITE_ID = 1

INSTALLED_APPS = (
    "django.contrib.contenttypes",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.humanize",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "djoser",
    "corsheaders",
    "storages",
    "anymail",
    "pagedown.apps.PagedownConfig",
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

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
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
            "class": "logging.handlers.WatchedFileHandler",
            "filename": FLAT_LOG_PATH,
            "formatter": "key_value",
        },
    },
    "loggers": {
        "django_structlog": {
            "handlers": ["console", "flat_line_file"],
            "level": "ERROR",
        },
        "stripe": {
            "handlers": ["console", "flat_line_file"] ,
            "level": "ERROR",
        },
        "core": {
            "handlers": ["console", "flat_line_file"],
            "level": "ERROR",
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

# See https://github.com/jrobichaud/django-structlog/issues/37 for why this is commented out
# @receiver(signals.bind_extra_request_metadata)
# def bind_user_email(request, logger, **kwargs):
#     structlog.contextvars.bind_contextvars(user_name=str(request.user))

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

ROOT_URLCONF = "bhmc.urls"

CORS_ORIGIN_ALLOW_ALL = True

WSGI_APPLICATION = "bhmc.wsgi.application"

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Chicago"

USE_I18N = False

USE_L10N = False

USE_TZ = True

