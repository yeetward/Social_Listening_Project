from typing import List, Dict, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import UpdateOne, MongoClient

MONGO_URI = "mongodb+srv://AI_Team_Database:46jdJQEZlhoSDagV@cluster0.dqugl74.mongodb.net/pace_database?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["pace_database"]

def write_ai_results_batch(history_id: ObjectId, items: List[Dict]) -> Tuple[int, int]:
    """
    Upsert a batch of ai_results for a given history_id.
    Each item should include at least: url, rank, ai_title, ai_summary.
    We upsert on (history_id, url).
    Returns (upserted_count, matched_updates)
    """
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
            # (optional) keep raw_id in sync if provided by caller
            "raw_id": it.get("raw_id"),
            # AI outputs
            "rank": it.get("rank"),
            "relevance_score": it.get("relevance_score"),
            "ai_title": it.get("ai_title"),
            "ai_summary": it.get("ai_summary"),
            "tags": it.get("tags"),
            "influencer_mentions": it.get("influencer_mentions"),
            "backlinks": it.get("backlinks"),
            # small passthroughs copied from raw
            "source": it.get("source"),
            "published_ts": it.get("published_ts"),
            # status → done unless caller overrides
            "status": it.get("status") or "done",
            "finished_at": now,
        }
        ops.append(UpdateOne(selector, {"$set": docset, "$setOnInsert": {"created_at": now}}, upsert=True))

    result = col.bulk_write(ops) if ops else None
    upserts = getattr(result, "upserted_count", 0) if result else 0
    updates = getattr(result, "modified_count", 0) if result else 0

    return upserts, updates