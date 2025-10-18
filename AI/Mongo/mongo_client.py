"""
MongoDB client for AI module.
Provides database connection and collection access.
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

_client = None
_db = None


def get_db():
    """Get MongoDB database instance."""
    global _client, _db
    if _db is None:
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        db_name = os.getenv("MONGODB_DBNAME", "pace_unit")
        _client = MongoClient(mongo_uri)
        _db = _client[db_name]
    return _db


def get_collection(name: str):
    """Get a specific MongoDB collection."""
    return get_db()[name]
