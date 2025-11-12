import os
import sys
from pathlib import Path

# Paths & import setup 
BASE_DIR = Path(__file__).resolve().parent          
WORKSPACE_ROOT = BASE_DIR.parent                   

for p in (BASE_DIR, WORKSPACE_ROOT):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

AI_DIRS = [BASE_DIR / "AI", WORKSPACE_ROOT / "AI"]
for ai in AI_DIRS:
    if ai.is_dir():
        parent = str(ai.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)

# .env support 
try:
    from dotenv import load_dotenv
    load_dotenv(WORKSPACE_ROOT / ".env")
    load_dotenv(BASE_DIR / ".env") 
except Exception:
    pass

# App flags 
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-key-change-me")
DEBUG = os.environ.get("DEBUG", "1") in ("1", "true", "True")
IS_FLASK = True 

# Third-party API keys / constants 
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY", "61c6baaf-f156-4fd7-8b94-005642818a11")
NEWSAPI_KEY      = os.environ.get("NEWSAPI_KEY", "11da17e92c5d487f874c914347697aec")
SERPAPI_KEY      = os.environ.get("SERPAPI_KEY", "62aef6d6cf4760d45568f2b6483029d361df42eff443ebbffe7063cb594ce6a3")

GOOGLE_TRENDS_GEO = os.environ.get("GOOGLE_TRENDS_GEO", "AU")
GOOGLE_TRENDS_TZ  = int(os.environ.get("GOOGLE_TRENDS_TZ", "-660"))  # SerpAPI quirk

# Reddit
REDDIT_CLIENT_ID     = os.environ.get("REDDIT_CLIENT_ID", "s3vW-RmhXYulBjKnMD1PMQ")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "hsyiwZ1PnyZKn1wsUtBr5y6f0vDvCg")
REDDIT_USER_AGENT    = os.environ.get("REDDIT_USER_AGENT", "AI Bot Listening by /u/Apprehensive_Air3734")

# Mongo 
MONGODB_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb+srv://edwardpandiya_db_user:BBfYj1Fc0hKH1WsD@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
MONGODB_DBNAME = os.environ.get("MONGODB_DBNAME", "pace_database")

# Server config (optional env overrides)
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
