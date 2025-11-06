# Backend/api/analytics.py
import time
from bson import ObjectId
from .persist import get_mongo_db

import requests
from datetime import datetime, timezone, timedelta

from .persist import _iso_z, get_mongo_db, get_company_profile
def global_top_topics(days: int = 30, limit: int = 20):
    """
    Return the most common HISTORY subjects (deduped) linked to completed AI results
    within the last X days.

    De-dup logic:
      - One vote per (history_id, subject), not per ai_results row.
      - Subjects are normalized (trim + lowercase) to avoid casing/whitespace dupes.
    """
    db = get_mongo_db()

    now_dt = datetime.now(timezone.utc)
    from_dt = now_dt - timedelta(days=days)

    pipeline = [
        # Only finished AI results
        {"$match": {"status": "done"}},

        # Join ai_results -> history
        {"$lookup": {
            "from": "history",
            "localField": "history_id",
            "foreignField": "_id",
            "as": "hist"
        }},
        {"$unwind": {"path": "$hist", "preserveNullAndEmptyArrays": False}},

        # Time window on history.created_at and require non-empty subject
        {"$match": {
            "hist.created_at": {"$gte": from_dt},
            "hist.subject": {"$type": "string", "$ne": ""}
        }},

        # Normalize subject to avoid dupes due to case/whitespace
        {"$set": {
            "norm_subject": {
                "$toLower": {
                    "$trim": {"input": "$hist.subject"}
                }
            }
        }},

        # De-dup per (history_id, normalized subject)
        {"$group": {
            "_id": {"hid": "$hist._id", "sub": "$norm_subject"}
        }},

        # Count unique histories per normalized subject
        {"$group": {
            "_id": "$_id.sub",
            "count": {"$sum": 1}
        }},

        {"$sort": {"count": -1}},
        {"$limit": max(1, int(limit))}
    ]

    rows = list(db["ai_results"].aggregate(pipeline))

    # Return the normalized subject strings
    return [r["_id"] for r in rows]


def trend_timeseries_by_day(history_id: ObjectId, days: int = 30):
    db = get_mongo_db()
    now_ms = int(time.time() * 1000)
    from_ms = now_ms - days * 86400 * 1000
    pipeline = [
        {"$match": {"history_id": history_id, "status": "done", "published_ts": {"$ne": None}}},
        {"$addFields": {"pub_dt": {"$toDate": {"$multiply": ["$published_ts", 1000]}}}},
        {"$match": {"pub_dt": {"$gte": {"$toDate": from_ms}}}},
        {"$group": {"_id": {"$dateTrunc": {"date": "$pub_dt", "unit": "day"}},
                    "count": {"$sum": 1},
                    "avg_relevance": {"$avg": "$relevance_score"}}},
        {"$sort": {"_id": 1}}
    ]
    return list(db["ai_results"].aggregate(pipeline))

def trend_top_tags(history_id: ObjectId, days: int = 30, top_k: int = 20):
    db = get_mongo_db()
    now_ms = int(time.time() * 1000)
    from_ms = now_ms - days * 86400 * 1000
    pipeline = [
        # 🆕 Changed: Now includes BOTH "queued" and "done" results for immediate tags
        {"$match": {"history_id": history_id, "status": {"$in": ["queued", "done"]}, "published_ts": {"$ne": None}}},
        {"$addFields": {"pub_dt": {"$toDate": {"$multiply": ["$published_ts", 1000]}}}},
        {"$match": {"pub_dt": {"$gte": {"$toDate": from_ms}}}},
        {"$unwind": {"path": "$tags", "preserveNullAndEmptyArrays": False}},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": top_k},
    ]
    return list(db["ai_results"].aggregate(pipeline))

def trend_by_source(history_id: ObjectId, days: int = 30):
    db = get_mongo_db()
    now_ms = int(time.time() * 1000)
    from_ms = now_ms - days * 86400 * 1000
    pipeline = [
        {"$match": {"history_id": history_id, "status": "done", "published_ts": {"$ne": None}}},
        {"$addFields": {"pub_dt": {"$toDate": {"$multiply": ["$published_ts", 1000]}}}},
        {"$match": {"pub_dt": {"$gte": {"$toDate": from_ms}}}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}, "avg_relevance": {"$avg": "$relevance_score"}}},
        {"$sort": {"count": -1}},
    ]
    return list(db["ai_results"].aggregate(pipeline))

def _as_list(val):
    """
    Accept list[str] or comma-separated str -> list[str]. Anything else -> [].
    """
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str):
        return [s.strip() for s in val.split(",") if s.strip()]
    return []


def _parse_iso_to_date(s: str | None):
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.astimezone(timezone.utc).date()
    except Exception:
        return None

def _coerce_topics_list(payload) -> list[str]:
    if isinstance(payload, list):
        return [str(x).strip() for x in payload if isinstance(x, str)]
    if isinstance(payload, dict) and isinstance(payload.get("topics"), list):
        return [str(x).strip() for x in payload["topics"] if isinstance(x, str)]
    return []

