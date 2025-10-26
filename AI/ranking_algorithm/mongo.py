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

    Each item should include:
      url, rank, relevance_score, ai_title, ai_summary, tags, source, published_ts
    Optional:
      per_algo_scores -> dict of {"bm25":..., "sbert":..., ...}

    We upsert on (history_id, url).

    Returns:
        (upserted_count, modified_count)
    """
    col = db["ai_results"]
    ops = []
    now = datetime.now(timezone.utc)

    for it in items:
        url = (it.get("url") or "").strip()
        if not url:
            continue

        selector = {
            "history_id": ObjectId(history_id),
            "url": url,
        }

        docset = {
            "history_id": ObjectId(history_id),
            "url": url,
            "raw_id": it.get("raw_id"),

            # AI ranking outputs
            "rank": it.get("rank"),
            "relevance_score": it.get("relevance_score"),
            "per_algo_scores": it.get("per_algo_scores"),  # <-- NEW (optional)

            # AI-generated enrichment
            "ai_title": it.get("ai_title"),
            "ai_summary": it.get("ai_summary"),
            "tags": it.get("tags"),
            "influencer_mentions": it.get("influencer_mentions"),
            "backlinks": it.get("backlinks"),

            # passthrough metadata
            "source": it.get("source"),
            "published_ts": it.get("published_ts"),

            # pipeline status
            "status": it.get("status") or "done",
            "finished_at": now,
        }

        ops.append(
            UpdateOne(
                selector,
                {
                    "$set": docset,
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
        )

    if not ops:
        return (0, 0)

    result = col.bulk_write(ops)
    upserts = getattr(result, "upserted_count", 0)
    updates = getattr(result, "modified_count", 0)

    return upserts, updates
