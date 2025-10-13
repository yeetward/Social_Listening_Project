# Backend/api/persist.py
from typing import Iterable, Tuple
from django.conf import settings
from pymongo import MongoClient
from pymongo.server_api import ServerApi


_mongo_client = None
_mongo_db = None


def get_mongo_db():
    """Return a cached MongoDB database handle using settings.MONGODB_URI/DBNAME."""
    global _mongo_client, _mongo_db
    if _mongo_db is not None:
        return _mongo_db

    uri = settings.MONGODB_URI
    dbname = settings.MONGODB_DBNAME

    if not uri or not dbname:
        raise RuntimeError("Mongo settings missing: MONGODB_URI / MONGODB_DBNAME")

    _mongo_client = MongoClient(uri, server_api=ServerApi("1"))
    _mongo_db = _mongo_client[dbname]
    return _mongo_db



def persist_posts(rows: Iterable[dict]) -> Tuple[int, int]:
    """
    Upsert posts into MongoDB 'posts' collection by URL.
    Returns (created_count, updated_count).
    """
    db = get_mongo_db()
    col = db["posts"]

    created = 0
    updated = 0

    for p in rows:
        url = (p.get("url") or "").strip()
        if not url:
            continue  

        doc = {
            "source_key": (p.get("source") or "").strip(),
            "post_id": p.get("post_id") or "",
            "url": url,
            "title": p.get("title") or "",
            "text": p.get("text") or "",
            "text_html": p.get("text_html") or "",
            "author": p.get("author") or "",
            "published_ts": p.get("published_ts"),
            "engagement": p.get("engagement") or {},
        }

        # Upsert by URL
        res = col.update_one({"url": url}, {"$set": doc}, upsert=True)
        # If upserted_id is set, we created; otherwise updated
        if res.upserted_id is not None:
            created += 1
        elif res.matched_count:
            updated += 1

    return created, updated








