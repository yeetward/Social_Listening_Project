import os
from pathlib import Path
from dotenv import load_dotenv

# PATH SETUP
BASE_DIR = Path(__file__).resolve().parent         
PROJECT_ROOT = BASE_DIR.parent                     
CREDENTIALS_DIR = PROJECT_ROOT / "credentials"      

AI_DIR = PROJECT_ROOT / "AI"
if AI_DIR.exists():
    ai_parent = str(AI_DIR.parent)
    if ai_parent not in os.sys.path:
        os.sys.path.insert(0, ai_parent)

# LOAD CREDENTIAL FILES
env_files = [
    CREDENTIALS_DIR / "backend.env",
]

for env_file in env_files:
    if env_file.exists():
        load_dotenv(env_file)

# APPLICATION FLAGS
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.environ.get("DEBUG", "1") in ("1", "true", "True")
IS_FLASK = True

# THIRD-PARTY API KEYS
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

GOOGLE_TRENDS_GEO = os.environ.get("GOOGLE_TRENDS_GEO", "AU")
GOOGLE_TRENDS_TZ = int(os.environ.get("GOOGLE_TRENDS_TZ", "-660"))

# REDDIT
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT")

# MONGODB
MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DBNAME = os.environ.get("MONGODB_DBNAME", "pace_database")

# SERVER CONFIG
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))