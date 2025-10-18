"""
Save article ranking scores to MongoDB.
Placeholder for compatibility with main.py imports.
"""

from typing import Dict, Any
from datetime import datetime
from .mongo_client import get_collection


def upsert_scores(
    article_id: Any,
    keyword: str,
    final_score: float,
    per_algo_scores: Dict[str, float]
) -> None:
    """
    Save or update ranking scores for an article.

    Args:
        article_id: The article ID (_id from posts collection)
        keyword: Search keyword used
        final_score: Combined final score
        per_algo_scores: Dictionary of individual algorithm scores
    """
    collection = get_collection("article_scores")

    score_doc = {
        "article_id": article_id,
        "keyword": keyword,
        "final_score": float(final_score),
        "algorithm_scores": {k: float(v) for k, v in per_algo_scores.items()},
        "updated_at": datetime.utcnow()
    }

    # Upsert (update if exists, insert if not)
    collection.update_one(
        {"article_id": article_id, "keyword": keyword},
        {"$set": score_doc},
        upsert=True
    )
