# # Backend/api/persist.py
# from typing import Iterable, Tuple
# from django.db import transaction
# from django.core.validators import URLValidator
# from django.core.exceptions import ValidationError
# from django.utils import timezone

# from pymongo import MongoClient
# from django.conf import settings

# from .models import Source, Post

# _url_validator = URLValidator()

# def _safe_url(url: str) -> str | None:
#     if not url:
#         return None
#     try:
#         _url_validator(url)
#         return url
#     except ValidationError:
#         return None

# def _ensure_source(source_key: str, source_name: str | None = None) -> Source:
#     # Prefer seeded names, but create if missing
#     name = source_name or source_key.replace("_", " ").title()
#     src, _ = Source.objects.get_or_create(key=source_key, defaults={"name": name})
#     return src

# def _epoch_to_dt_utc(ts: int | float | None):
#     if not ts:
#         return None
#     try:
#         # guard ms vs sec
#         ts = float(ts)
#         if ts > 1e12:
#             ts = ts / 1000.0
#         return timezone.datetime.fromtimestamp(int(ts), tz=timezone.utc)
#     except Exception:
#         return None


# def get_mongo_collection(collection_name):
#     """Get MongoDB collection directly"""
#     client = MongoClient(settings.DATABASES['default']['CLIENT']['host'])
#     db = client[settings.DATABASES['default']['NAME']]
#     return db[collection_name]

# def persist_posts(rows):
#     """MongoDB-native persistence"""
#     collection = get_mongo_collection('posts')
    
#     for post in rows:
#         # Convert to MongoDB document
#         document = {
#             'source_key': post.get('source'),
#             'post_id': post.get('post_id'),
#             'url': post.get('url'),
#             'title': post.get('title'),
#             'text': post.get('text'),
#             'text_html': post.get('text_html'),
#             'author': post.get('author'),
#             'published_at': post.get('published_at'),
#             'published_ts': post.get('published_ts'),
#             'engagement': post.get('engagement', {}),
#             'created_at': post.get('created_at'),
#             'updated_at': post.get('updated_at')
#         }
        
#         # Upsert by URL
#         collection.update_one(
#             {'url': document['url']},
#             {'$set': document},
#             upsert=True
#         )
# # @transaction.atomic
# # def persist_posts(rows: Iterable[dict]) -> Tuple[int, int]:
# #     """
# #     Upsert posts by URL. Returns (created_count, updated_count).
# #     Expected row shape (matches your fetchers):
# #       {
# #         "post_id": str,
# #         "source": "reddit_rss" | "news_rss" | ...,
# #         "url": str,
# #         "title": str,
# #         "text": str,
# #         "text_html": str,
# #         "published_ts": int | None,
# #         "author": str,
# #         "engagement": dict | None,
# #       }
# #     """
# #     created, updated = 0, 0

# #     for p in rows:
# #         url = _safe_url(p.get("url"))
# #         if not url:
# #             # skip invalid/missing URL to avoid DB junk
# #             continue

# #         source_key = (p.get("source") or "").strip() or "unknown"
# #         src = _ensure_source(source_key)

# #         published_ts = p.get("published_ts")
# #         published_at = _epoch_to_dt_utc(published_ts)

# #         defaults = {
# #             "source": src,
# #             "post_id": p.get("post_id") or "",
# #             "title": p.get("title") or "",
# #             "text": p.get("text") or "",
# #             "text_html": p.get("text_html") or "",
# #             "author": p.get("author") or "",
# #             "published_at": published_at,
# #             "published_ts": int(published_ts) if isinstance(published_ts, (int, float)) else None,
# #             "engagement": p.get("engagement"),
# #         }

# #         obj, was_created = Post.objects.update_or_create(
# #             url=url,
# #             defaults=defaults
# #         )
# #         if was_created:
# #             created += 1
# #         else:
# #             updated += 1

# #     return created, updated

# Backend/api/persist.py
# Backend/api/persist.py
# Backend/api/persist.py
# Backend/api/persist.py
from typing import Iterable, Tuple
from django.conf import settings
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Reuse a single client for the process
_mongo_client = None
_mongo_db = None

def get_mongo_db():
    """Return a cached MongoDB database handle using settings.MONGODB_URI/DBNAME."""
    global _mongo_client, _mongo_db
    if _mongo_db:
        return _mongo_db

    uri = settings.MONGODB_URI
    dbname = settings.MONGODB_DBNAME

    if not uri or not dbname:
        raise RuntimeError("Mongo settings missing: MONGODB_URI / MONGODB_DBNAME")

    # ServerApi is recommended by Atlas quickstart
    _mongo_client = MongoClient(uri, server_api=ServerApi("1"))
    # Optional ping (uncomment if you want startup validation)
    # _mongo_client.admin.command("ping")
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
            continue  # skip junk rows

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
        # Heuristic: if upserted_id is set, we created; otherwise updated
        if res.upserted_id is not None:
            created += 1
        elif res.matched_count:
            updated += 1

    return created, updated