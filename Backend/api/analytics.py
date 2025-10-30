# Backend/api/analytics.py
import time
from bson import ObjectId
from .persist import get_mongo_db
import time

def global_top_topics(days: int = 30, limit: int = 20):
    """
    Return the most common topic tags from all AI results within the last X days.
    Outputs a list of strings (topic names).
    """
    db = get_mongo_db()

    # Convert to seconds since epoch
    now_sec = int(time.time())
    from_sec = now_sec - days * 86400

    pipeline = [
        # Match only completed AI results with tags
        {"$match": {
            "status": "done",
            "published_ts": {"$gte": from_sec},  # compare using seconds (not ms)
            "tags": {"$type": "array", "$ne": []}
        }},
        # Flatten tags array
        {"$unwind": {"path": "$tags", "preserveNullAndEmptyArrays": False}},
        # Group and count each tag
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]

    # Run pipeline
    rows = list(db["ai_results"].aggregate(pipeline))

    # Return only the topic names as a list of strings
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
        {"$match": {"history_id": history_id, "status": "done", "published_ts": {"$ne": None}}},
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