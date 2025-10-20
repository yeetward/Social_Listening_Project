# # Backend/api/persist.py
# from typing import Iterable, Tuple
# from django.conf import settings
# from pymongo import MongoClient
# from pymongo.server_api import ServerApi


# _mongo_client = None
# _mongo_db = None


# def get_mongo_db():
#     """Return a cached MongoDB database handle using settings.MONGODB_URI/DBNAME."""
#     global _mongo_client, _mongo_db
#     if _mongo_db is not None:
#         return _mongo_db

#     uri = settings.MONGODB_URI
#     dbname = settings.MONGODB_DBNAME

#     if not uri or not dbname:
#         raise RuntimeError("Mongo settings missing: MONGODB_URI / MONGODB_DBNAME")

#     _mongo_client = MongoClient(uri, server_api=ServerApi("1"))
#     _mongo_db = _mongo_client[dbname]
#     return _mongo_db



# def persist_posts(rows: Iterable[dict]) -> Tuple[int, int]:
#     """
#     Upsert posts into MongoDB 'posts' collection by URL.
#     Returns (created_count, updated_count).
#     """
#     db = get_mongo_db()
#     col = db["posts"]

#     created = 0
#     updated = 0

#     for p in rows:
#         url = (p.get("url") or "").strip()
#         if not url:
#             continue  

#         doc = {
#             "source_key": (p.get("source") or "").strip(),
#             "post_id": p.get("post_id") or "",
#             "url": url,
#             "title": p.get("title") or "",
#             "text": p.get("text") or "",
#             "text_html": p.get("text_html") or "",
#             "author": p.get("author") or "",
#             "published_ts": p.get("published_ts"),
#             "engagement": p.get("engagement") or {},
#         }

#         # Upsert by URL
#         res = col.update_one({"url": url}, {"$set": doc}, upsert=True)
#         # If upserted_id is set, we created; otherwise updated
#         if res.upserted_id is not None:
#             created += 1
#         elif res.matched_count:
#             updated += 1

#     return created, updated






# Backend/api/persist.py
# Backend/api/persist.py
# Backend/api/persist.py




# from typing import Iterable, Tuple, Dict, Any
# from datetime import datetime
# from bson import ObjectId
# from django.conf import settings
# from pymongo import MongoClient
# from pymongo.server_api import ServerApi

# _mongo_client = None
# _mongo_db = None

# def get_mongo_db():
#     """
#     Cached MongoDB database handle using settings.MONGODB_URI/DBNAME.
#     """
#     global _mongo_client, _mongo_db
#     if _mongo_db is not None:
#         return _mongo_db

#     uri = settings.MONGODB_URI
#     dbname = settings.MONGODB_DBNAME
#     if not uri or not dbname:
#         raise RuntimeError("Mongo settings missing: MONGODB_URI / MONGODB_DBNAME")

#     _mongo_client = MongoClient(uri, server_api=ServerApi("1"))
#     _mongo_db = _mongo_client[dbname]
#     return _mongo_db


# # ---------- HISTORY DOCS ----------

# def create_history(*, subject: str, location: str, industry: str,
#                    sources_used: list[str], params: Dict[str, Any]) -> ObjectId:
#     """
#     Insert a new 'history' document and return its _id.
#     """
#     db = get_mongo_db()
#     now = datetime.utcnow()
#     doc = {
#         "subject": subject,
#         "location": location,
#         "industry": industry,
#         "sources_used": sources_used,
#         "params": params or {},
#         "created_at": now,

#         # AI status (AI worker will update these)
#         "ai_ready": False,
#         "ai_count": 0,
#         "ai_target": 100,
#         "started_at": now,
#         "last_updated": None,
#         "finished_at": None,
#     }
#     res = db["history"].insert_one(doc)
#     return res.inserted_id


# # ---------- RAW INSIGHTS UPSERT ----------

# def persist_raw_insights(rows: Iterable[dict], history_id: ObjectId, *, cap: int = 500) -> Tuple[int, int, int]:
#     """
#     Upsert up to 'cap' docs into 'raw_insights' by URL; add the history_id to 'histories' array.
#     Returns (created_count, updated_count, seen_after_dedupe).
#     """
#     db = get_mongo_db()
#     col = db["raw_insights"]

#     created = 0
#     updated = 0
#     count = 0
#     seen_urls = set()

#     for p in rows:
#         if count >= cap:
#             break

#         url = (p.get("url") or "").strip()
#         if not url or url in seen_urls:
#             continue
#         seen_urls.add(url)

#         doc = {
#             "source": (p.get("source") or "").strip(),
#             "post_id": p.get("post_id") or "",
#             "url": url,
#             "title": p.get("title") or "",
#             "text": p.get("text") or "",
#             "text_html": p.get("text_html") or "",
#             "author": p.get("author") or "",
#             "published_ts": p.get("published_ts"),
#             "engagement": p.get("engagement") or None,
#             "created_at": datetime.utcnow(),
#         }

#         # Upsert by URL + push history link
#         res = col.update_one(
#             {"url": url},
#             {
#                 "$setOnInsert": {"created_at": doc["created_at"]},
#                 "$set": {
#                     "source": doc["source"],
#                     "post_id": doc["post_id"],
#                     "title": doc["title"],
#                     "text": doc["text"],
#                     "text_html": doc["text_html"],
#                     "author": doc["author"],
#                     "published_ts": doc["published_ts"],
#                     "engagement": doc["engagement"],
#                 },
#                 "$addToSet": {"histories": history_id},
#             },
#             upsert=True,
#         )
#         if res.upserted_id is not None:
#             created += 1
#         elif res.matched_count:
#             updated += 1

#         count += 1

#     return created, updated, len(seen_urls)

# Backend/api/persist.py
# Backend/api/persist.py
from typing import Iterable, Tuple, List, Dict, Optional
from datetime import datetime, timezone
from bson import ObjectId
from django.conf import settings
from pymongo import MongoClient, UpdateOne
from pymongo.server_api import ServerApi

_mongo_client = None
_mongo_db = None

# -------------------- core connection --------------------

def get_mongo_db():
    """
    Return a cached MongoDB database handle using settings.MONGODB_URI/DBNAME.
    """
    global _mongo_client, _mongo_db
    if _mongo_db is not None:            # IMPORTANT: compare with None (pymongo objects are not truthy)
        return _mongo_db

    uri = settings.MONGODB_URI
    dbname = settings.MONGODB_DBNAME
    if not uri or not dbname:
        raise RuntimeError("Mongo settings missing: MONGODB_URI / MONGODB_DBNAME")

    _mongo_client = MongoClient(uri, server_api=ServerApi("1"))
    _mongo_db = _mongo_client[dbname]
    return _mongo_db

# -------------------- HISTORY helpers --------------------

def create_history(
    subject: str,
    location: str,
    industry: str,
    sources_used: List[str],
    params: Dict,
    ai_target: int = 100
) -> ObjectId:
    """
    Inserts a new history document and returns its _id.
    """
    db = get_mongo_db()
    doc = {
        "subject": subject,
        "location": location,
        "industry": industry,
        "sources_used": sources_used,
        "params": params or {},
        "created_at": datetime.now(timezone.utc),
        # AI status
        "ai_ready": False,
        "ai_count": 0,
        "ai_target": ai_target,
        "started_at": None,
        "last_updated": None,
        "finished_at": None,
    }
    res = db["history"].insert_one(doc)
    return res.inserted_id

def mark_history_ai_started(history_id: ObjectId):
    db = get_mongo_db()
    now = datetime.now(timezone.utc)
    db["history"].update_one(
        {"_id": ObjectId(history_id)},
        {"$set": {"started_at": now, "last_updated": now}}
    )

def mark_history_ai_progress(history_id: ObjectId, ai_count: int):
    db = get_mongo_db()
    now = datetime.now(timezone.utc)
    db["history"].update_one(
        {"_id": ObjectId(history_id)},
        {"$set": {"ai_count": ai_count, "last_updated": now}}
    )

def mark_history_ai_done(history_id: ObjectId, total_count: Optional[int] = None):
    db = get_mongo_db()
    now = datetime.now(timezone.utc)
    updates = {"ai_ready": True, "finished_at": now, "last_updated": now}
    if total_count is not None:
        updates["ai_count"] = total_count
    db["history"].update_one({"_id": ObjectId(history_id)}, {"$set": updates})

# -------------------- RAW INSIGHTS --------------------

def persist_raw_insights(rows: Iterable[dict]) -> Tuple[int, int]:
    """
    Upsert rows into 'raw_insights' by unique 'url'.
    Returns (created_count, updated_count).
    """
    db = get_mongo_db()
    col = db["raw_insights"]

    created = 0
    updated = 0
    for p in rows:
        url = (p.get("url") or "").strip()
        if not url:
            continue

        doc = {
            "url": url,
            "source": (p.get("source") or "").strip(),
            "title": p.get("title") or "",
            "text": p.get("text") or "",
            "text_html": p.get("text_html") or "",
            "author": p.get("author") or None,
            "published_ts": p.get("published_ts"),
            "engagement": p.get("engagement") or None,
            # enrichment candidates (may be None at ingest time)
            "tags": p.get("tags") if "tags" in p else None,
            "influencer_mentions": p.get("influencer_mentions") if "influencer_mentions" in p else None,
            "backlinks": p.get("backlinks") if "backlinks" in p else None,
            "created_at": datetime.now(timezone.utc),
        }

        res = col.update_one({"url": url}, {"$set": doc}, upsert=True)
        if res.upserted_id is not None:
            created += 1
        elif res.matched_count:
            updated += 1

    return created, updated

# -------------------- AI RESULTS --------------------

def write_ai_results_batch(history_id: ObjectId, items: List[Dict]) -> Tuple[int, int]:
    """
    Upsert a batch of ai_results for a given history_id.
    Each item should include at least: url, rank, ai_title, ai_summary.
    We upsert on (history_id, url).
    Returns (upserted_count, matched_updates)
    """
    db = get_mongo_db()
    col = db["ai_results"]

    ops = []
    now = datetime.now(timezone.utc)
    for it in items:
        url = it.get("url")
        if not url:
            continue

        selector = {"history_id": ObjectId(history_id), "url": url}
        docset = {
            "history_id": ObjectId(history_id),
            "url": url,
            "rank": it.get("rank"),
            "relevance_score": it.get("relevance_score"),
            "ai_title": it.get("ai_title"),
            "ai_summary": it.get("ai_summary"),
            "tags": it.get("tags"),
            "influencer_mentions": it.get("influencer_mentions"),
            "backlinks": it.get("backlinks"),
            "source": it.get("source"),
            "published_ts": it.get("published_ts"),
            "created_at": now,
        }
        ops.append(UpdateOne(selector, {"$set": docset}, upsert=True))

    result = col.bulk_write(ops) if ops else None
    upserts = getattr(result, "upserted_count", 0) if result else 0
    updates = getattr(result, "modified_count", 0) if result else 0
    return upserts, updates

# -------------------- Legacy shim (keeps old imports working) --------------------

def persist_posts(rows: Iterable[dict]) -> Tuple[int, int]:
    """
    Backward-compatible shim that writes into 'raw_insights'.
    (Older code called persist_posts; we now store to raw_insights.)
    """
    return persist_raw_insights(rows)