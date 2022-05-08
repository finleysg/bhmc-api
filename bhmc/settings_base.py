import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.RemoteUserMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
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
        "rest_framework.authentication.SessionAuthentication",
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

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

ROOT_URLCONF = "bhmc.urls"

CORS_ORIGIN_ALLOW_ALL = True

WSGI_APPLICATION = "bhmc.wsgi.application"

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Chicago"

USE_I18N = False

USE_L10N = False

USE_TZ = True

