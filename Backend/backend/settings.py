import sys, os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# -------------------------------------------------------------------
# Secrets & API keys
# -------------------------------------------------------------------
SECRET_KEY = "dev-only-secret-key-change-me"
DEBUG = True
ALLOWED_HOSTS = []

GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY", "61c6baaf-f156-4fd7-8b94-005642818a11")

# REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
# REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
# REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "PaceDiscoveryBot/1.0 (+team)")

# Add Reddit API credentials here:
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "s3vW-RmhXYulBjKnMD1PMQ")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "hsyiwZ1PnyZKn1wsUtBr5y6f0vDvCg")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "AI Bot Listening by /u/Apprehensive_Air3734")

# -------------------------------------------------------------------
# MongoDB Atlas (hard-coded per your request)
#   NOTE: PyMongo (in persist.py) will use these settings directly.
# -------------------------------------------------------------------
MONGODB_URI = (
    "mongodb+srv://edwardpandiya_db_user:BBfYj1Fc0hKH1WsD"
    "@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
MONGODB_DBNAME = "pace_database"

# -------------------------------------------------------------------
# Applications
# -------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "backend.wsgi.application"

# -------------------------------------------------------------------
# Databases (SQLite only for Django internals)
#   We are NOT using djongo. Persistence to Mongo is done via PyMongo.
# -------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# -------------------------------------------------------------------
# Password validation
# -------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -------------------------------------------------------------------
# I18N / TZ
# -------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# -------------------------------------------------------------------
# Static
# -------------------------------------------------------------------
STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# -------------------------------------------------------------------
# CORS (dev-friendly defaults)
# -------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True