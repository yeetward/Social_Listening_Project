from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
import os

# Load the env file that is NEXT TO this script
ENV_PATH = Path(__file__).resolve().parent / "mongo_credentials.env"
load_dotenv(ENV_PATH)

_client = None
_db = None

def get_db():
    global _client, _db
    if _db is None:
        uri = os.getenv("MONGODB_URI")
        dbname = os.getenv("MONGODB_DBNAME", "pace_unit")
        if not uri:
            raise RuntimeError(f"MONGODB_URI missing. Expected in {ENV_PATH}")
        _client = MongoClient(uri)
        _db = _client[dbname]
    return _db

def get_collection(name: str):
    return get_db()[name]
