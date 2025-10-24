# Backend/api/analytics.py
import time
from bson import ObjectId
from .persist import get_mongo_db
def global_top_topics(days: int = 30, limit: int = 20):
    """
    Return the most common tags (topics) from all AI results within the last X days.
    """
    db = get_mongo_db()
    now_ms = int(time.time() * 1000)
    from_ms = now_ms - days * 86400 * 1000

    pipeline = [
        {"$match": {"status": "done", "published_ts": {"$ne": None}}},
        {"$addFields": {"pub_dt": {"$toDate": {"$multiply": ["$published_ts", 1000]}}}},
        {"$match": {"pub_dt": {"$gte": {"$toDate": from_ms}}}},
        {"$unwind": {"path": "$tags", "preserveNullAndEmptyArrays": False}},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]

    return list(db["ai_results"].aggregate(pipeline))

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