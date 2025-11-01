# Backend/api/persist.py

from typing import Iterable, Tuple, List, Dict, Optional
from datetime import datetime, timezone, timedelta
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
    if _mongo_db is not None:  # IMPORTANT: compare with None (pymongo objects are not truthy)
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
    ai_target: int = 100,
    ttl_days: Optional[int] = None,
) -> ObjectId:
    """
    Inserts a new history document and returns its _id.
    """
    db = get_mongo_db()
    now = datetime.now(timezone.utc)
    doc = {
        "subject": subject,
        "location": location,
        "industry": industry,
        "sources_used": sources_used,
        "params": params or {},
        "created_at": now,
        # AI status
        "ai_ready": False,
        "ai_count": 0,
        "ai_target": ai_target,
        "started_at": None,
        "last_updated": None,
        "finished_at": None,
    }
    if ttl_days:
        doc["expires_at"] = now + timedelta(days=ttl_days)

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
    now = datetime.now(timezone.utc)

    for p in rows:
        url = (p.get("url") or "").strip()
        if not url:
            continue

        res = col.update_one(
            {"url": url},
            {
                "$set": {
                    "url": url,
                    "source": (p.get("source") or "").strip(),
                    "title": p.get("title") or "",
                    "text": p.get("text") or "",
                    "text_html": p.get("text_html") or "",
                    "author": p.get("author") or None,
                    "published_ts": p.get("published_ts"),
                    "engagement": p.get("engagement") or None,
                    "tags": p.get("tags") if "tags" in p else None,
                    "influencer_mentions": p.get("influencer_mentions") if "influencer_mentions" in p else None,
                    "backlinks": p.get("backlinks") if "backlinks" in p else None,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True
        )

        if res.upserted_id is not None:
            created += 1
        elif res.matched_count:
            updated += 1

    return created, updated

# -------------------- AI RESULTS (queue + output) --------------------

def seed_ai_result_stubs(history_id: ObjectId, rows: Iterable[dict]) -> int:
    """
    Create 'queued' ai_results stubs for this run, one per URL.
    Idempotent upserts keyed by (history_id, url).
    Returns number of upserts attempted.
    """
    db = get_mongo_db()
    now = datetime.now(timezone.utc)

    urls = [(p.get("url") or "").strip() for p in rows if p.get("url")]
    urls = [u for u in urls if u]
    if not urls:
        return 0

    raw_map = {
        r["url"]: r["_id"]
        for r in db["raw_insights"].find({"url": {"$in": urls}}, {"_id": 1, "url": 1})
    }

    ops = []
    for p in rows:
        url = (p.get("url") or "").strip()
        if not url:
            continue

        selector = {"history_id": ObjectId(history_id), "url": url}
        set_on_insert = {
            "history_id": ObjectId(history_id),
            "url": url,
            "raw_id": raw_map.get(url),
            "source": (p.get("source") or "").strip(),
            "published_ts": p.get("published_ts"),
            "status": "queued",
            "created_at": now,
        }
        ops.append(UpdateOne(selector, {"$setOnInsert": set_on_insert}, upsert=True))

    if ops:
        db["ai_results"].bulk_write(ops)
    return len(ops)


def write_ai_results_batch(history_id: ObjectId, items: List[Dict]) -> Tuple[int, int]:
    """
    Upsert a batch of ai_results for a given history_id.
    Each item should include at least: url, rank, ai_title, ai_summary.
    """
    db = get_mongo_db()
    col = db["ai_results"]

    ops = []
    now = datetime.now(timezone.utc)
    for it in items:
        url = (it.get("url") or "").strip()
        if not url:
            continue

        selector = {"history_id": ObjectId(history_id), "url": url}
        docset = {
            "history_id": ObjectId(history_id),
            "url": url,
            "raw_id": it.get("raw_id"),
            "rank": it.get("rank"),
            "relevance_score": it.get("relevance_score"),
            "ai_title": it.get("ai_title"),
            "ai_summary": it.get("ai_summary"),
            "tags": it.get("tags"),
            "influencer_mentions": it.get("influencer_mentions"),
            "backlinks": it.get("backlinks"),
            "source": it.get("source"),
            "published_ts": it.get("published_ts"),
            "status": it.get("status") or "done",
            "finished_at": now,
        }
        ops.append(UpdateOne(selector, {"$set": docset, "$setOnInsert": {"created_at": now}}, upsert=True))

    result = col.bulk_write(ops) if ops else None
    upserts = getattr(result, "upserted_count", 0) if result else 0
    updates = getattr(result, "modified_count", 0) if result else 0
    return upserts, updates

# -------------------- Legacy shim --------------------

def persist_posts(rows: Iterable[dict]) -> Tuple[int, int]:
    """
    Backward-compatible shim that writes into 'raw_insights'.
    """
    return persist_raw_insights(rows)

# ---------------------- Company profile helpers ---------------------------------------

def _iso_z(dt: datetime) -> str:
    """Convert a datetime to ISO string with Z suffix (UTC)."""
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_card_block(now: datetime) -> dict:
    """Return default structure for each company card."""
    return {
        "data": [],
        "updated_at": None,
        "next_refresh_at": _iso_z(now + timedelta(days=7)),
    }


def upsert_company_profile(profile: dict):
    """
    Insert or update a company profile by name with card placeholders.
    Expected keys: { name: str, description: str, competitors?: list[str] }
    """
    db = get_mongo_db()
    now = datetime.now(timezone.utc)

    name = (profile.get("name") or "").strip()
    desc = (profile.get("description") or "").strip()
    comps = profile.get("competitors", [])
    if not name:
        raise ValueError("company profile name is required")

    if comps is None:
        comps = []
    if not isinstance(comps, list):
        raise ValueError("competitors must be a list of strings")
    comps = sorted({str(c).strip() for c in comps if str(c).strip()})

    # Default cards for each section
    cards = {
        "trending": _default_card_block(now),
        "newsfeed": _default_card_block(now),
        "ideas": _default_card_block(now),
        "backlinks": _default_card_block(now),
        "opportunities": _default_card_block(now),
    }

    db["company_profiles"].update_one(
        {"name": name},
        {
            "$set": {
                "name": name,
                "description": desc,
                "competitors": comps,
                "cards": cards,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True
    )


def get_company_profile(name: Optional[str] = None) -> Optional[dict]:
    """
    Return one company profile.
    - If `name` is provided, return that specific profile.
    - Else, return the most recently created one.
    """
    db = get_mongo_db()
    if name:
        return db["company_profiles"].find_one({"name": name})
    return db["company_profiles"].find_one(sort=[("created_at", -1)])