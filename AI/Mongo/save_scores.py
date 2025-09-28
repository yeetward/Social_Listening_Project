# AI/Mongo/save_scores.py
"""
Upsert scoring results to MongoDB.

"""

from typing import Dict, Any
from AI.Mongo.mongo_client import get_db


def upsert_scores(doc_id: Any, keyword: str, final_score: float, per_algo: Dict[str, float]) -> None:
    db = get_db()
    db["scores"].update_one(
        {"post_id": doc_id, "keyword": keyword},
        {
            "$set": {
                "post_id": doc_id,
                "keyword": keyword,
                "final_score": float(final_score),
                "per_algo": {k: float(v) for k, v in (per_algo or {}).items()},
            }
        },
        upsert=True,
    )
