# Backend/api/mongo.py
from django.conf import settings
from pymongo import MongoClient

_client = None
_db = None

def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(settings.MONGODB_URI)
        _db = _client[settings.MONGODB_DBNAME]
    return _db

def get_collection(name: str):
    return get_db()[name]