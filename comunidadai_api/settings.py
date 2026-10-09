import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=False)

DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-only-insecure-key-change-before-deploy")
if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith("replace-with")):
    raise ImproperlyConfigured("Set a unique DJANGO_SECRET_KEY in production.")
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS or all(host in {"localhost", "127.0.0.1"} for host in ALLOWED_HOSTS)):
    raise ImproperlyConfigured("Set DJANGO_ALLOWED_HOSTS to the production API hostname(s).")

public_root = os.getenv("PUBLIC_ROOT", "").strip()
if not DEBUG and not public_root:
    raise ImproperlyConfigured("Set PUBLIC_ROOT to the frontend document root for static and uploaded files.")
PUBLIC_ROOT = Path(public_root).expanduser().resolve() if public_root else BASE_DIR / "public"
if not DEBUG and (PUBLIC_ROOT == BASE_DIR or PUBLIC_ROOT in BASE_DIR.parents or BASE_DIR in PUBLIC_ROOT.parents):
    raise ImproperlyConfigured("Keep the backend source and frontend document root in separate directories.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    'rest_framework_simplejwt',
    "drf_spectacular",
    "core",
    "django_extensions",
]

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]
if not DEBUG and (
    not CORS_ALLOWED_ORIGINS
    or any(not origin.startswith("https://") for origin in CORS_ALLOWED_ORIGINS)
):
    raise ImproperlyConfigured("Set CORS_ALLOWED_ORIGINS to the exact HTTPS frontend origin(s).")
CORS_ALLOW_HEADERS = ["accept", "authorization", "content-type", "origin", "x-csrftoken"]
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOW_CREDENTIALS = True

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "comunidadai_api.urls"

TEMPLATES = [{
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
}]

WSGI_APPLICATION = "comunidadai_api.wsgi.application"

USE_POSTGRES = os.getenv("USE_POSTGRES", "False" if DEBUG else "True") == "True"

if USE_POSTGRES:
    required_db_settings = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST")
    missing_db_settings = [key for key in required_db_settings if not os.getenv(key)]
    if missing_db_settings:
        raise ImproperlyConfigured("Missing PostgreSQL settings: " + ", ".join(missing_db_settings))
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": ({"sslmode": os.getenv("DB_SSLMODE")} if os.getenv("DB_SSLMODE") else {}),
        }
    }
else:
    if not DEBUG:
        raise ImproperlyConfigured("Enable PostgreSQL for non-debug deployments by setting USE_POSTGRES=True.")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = Path(os.getenv("STATIC_ROOT", str(PUBLIC_ROOT / "static"))).expanduser().resolve()
DOMAIN = os.getenv("DOMAIN", "").rstrip("/")
MEDIA_URL = "/comunidadia_uploads/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(PUBLIC_ROOT / "comunidadia_uploads"))).expanduser().resolve()
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(5 * 1024 * 1024)))
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
REFRESH_COOKIE_NAME = "comunidadia_refresh"
REFRESH_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "False" if DEBUG else "True") == "True"
REFRESH_COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False" if DEBUG else "True") == "True"
# Enable HSTS only after HTTPS has been confirmed on every production hostname.
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False") == "True"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "False") == "True"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'core.auth.JWTAuthenticationCustom',
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "200/day",
        "user": "2000/day",
        "auth": "10/minute",
        "chat": "30/minute",
    },
}

# Email Configuration
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
raw_from = os.getenv("DEFAULT_FROM_EMAIL", "").strip()
if not raw_from:
    DEFAULT_FROM_EMAIL = f"Comunidad IA <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else "no-reply@pedagogiavirtual.com"
elif "@" not in raw_from:
    DEFAULT_FROM_EMAIL = f"{raw_from} <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else raw_from
else:
    DEFAULT_FROM_EMAIL = raw_from
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
if not DEBUG:
    if EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
        raise ImproperlyConfigured("Configure an SMTP or production email backend; console email is not valid in production.")
    if EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
        missing_email_settings = [
            name for name, value in {
                "EMAIL_HOST": EMAIL_HOST,
                "EMAIL_HOST_USER": EMAIL_HOST_USER,
                "EMAIL_HOST_PASSWORD": EMAIL_HOST_PASSWORD,
                "DEFAULT_FROM_EMAIL": raw_from,
            }.items() if not value
        ]
        if missing_email_settings:
            raise ImproperlyConfigured("Missing production email settings: " + ", ".join(missing_email_settings))
        if EMAIL_USE_TLS and EMAIL_USE_SSL:
            raise ImproperlyConfigured("Use either EMAIL_USE_TLS or EMAIL_USE_SSL, not both.")
    if not DOMAIN.startswith("https://") or not FRONTEND_URL.startswith("https://"):
        raise ImproperlyConfigured("Set DOMAIN and FRONTEND_URL to their public HTTPS URLs.")
    if any(".example" in value or "your-domain" in value for value in [DOMAIN, FRONTEND_URL, *ALLOWED_HOSTS, *CORS_ALLOWED_ORIGINS]):
        raise ImproperlyConfigured("Replace all example domains with the real production domains.")
    if EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and (
        EMAIL_HOST_PASSWORD.startswith("replace-with")
        or any(".example" in value or "your-domain" in value for value in (EMAIL_HOST, EMAIL_HOST_USER, raw_from))
    ):
        raise ImproperlyConfigured("Replace the example SMTP host, account, sender, and password with real values.")
    if "CPANEL_USER" in str(PUBLIC_ROOT):
        raise ImproperlyConfigured("Replace the PUBLIC_ROOT example path with the actual cPanel document root.")
    if USE_POSTGRES and any(
        os.getenv(name, "").startswith("replace-with")
        for name in ("DB_NAME", "DB_USER", "DB_PASSWORD")
    ):
        raise ImproperlyConfigured("Replace the PostgreSQL example credentials with the real cPanel database values.")
    for setting_name, configured_path in (("STATIC_ROOT", STATIC_ROOT), ("MEDIA_ROOT", MEDIA_ROOT)):
        try:
            configured_path.relative_to(PUBLIC_ROOT)
        except ValueError as exc:
            raise ImproperlyConfigured(f"{setting_name} must be within PUBLIC_ROOT so Apache can serve it.") from exc

SPECTACULAR_SETTINGS = {
    "TITLE": "ComunidadAI API",
    "DESCRIPTION": "backend de ComunidadAI API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        }
    },
    "SECURITY": [{"BearerAuth": []}],
}

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3.8-flash")

# Config JWT (tiempos desde .env)
ACCESS_MIN = int(os.getenv("JWT_ACCESS_MINUTES", "30"))
REFRESH_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "7"))
JWT_CONFIG = {
    "ACCESS_LIFETIME": timedelta(minutes=ACCESS_MIN),
    "REFRESH_LIFETIME": timedelta(days=REFRESH_DAYS),
}
