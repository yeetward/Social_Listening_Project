"""
Save content distribution recommendations to MongoDB.
"""

from typing import Dict, List, Tuple, Any
from datetime import datetime
from .mongo_client import get_collection


def upsert_distribution_recommendation(
    article_id: Any,
    recommendations: List[Tuple[str, float]],
    metadata: Dict[str, Any] = None
) -> None:
    """
    Save or update distribution recommendations for an article.

    Args:
        article_id: The article ID (_id from posts collection)
        recommendations: List of (channel, score) tuples
        metadata: Optional metadata about the recommendation (e.g., weights used)
    """
    collection = get_collection("distribution_recommendations")

    # Prepare recommendation document
    rec_doc = {
        "article_id": article_id,
        "recommendations": [
            {"channel": ch, "score": float(sc)}
            for ch, sc in recommendations
        ],
        "updated_at": datetime.utcnow(),
        "metadata": metadata or {}
    }

    # Upsert (update if exists, insert if not)
    collection.update_one(
        {"article_id": article_id},
        {"$set": rec_doc},
        upsert=True
    )


def upsert_distribution_batch(
    results: List[Dict[str, Any]]
) -> int:
    """
    Save distribution recommendations for multiple articles.

    Args:
        results: List of dictionaries with _id and recommendations

    Returns:
        Number of documents updated/inserted
    """
    collection = get_collection("distribution_recommendations")
    count = 0

    for result in results:
        article_id = result.get("_id")
        recommendations = result.get("recommendations", [])

        if article_id:
            rec_doc = {
                "article_id": article_id,
                "recommendations": recommendations,
                "updated_at": datetime.utcnow(),
                "metadata": result.get("metadata", {})
            }

            collection.update_one(
                {"article_id": article_id},
                {"$set": rec_doc},
                upsert=True
            )
            count += 1

    return count


def get_distribution_recommendation(article_id: Any) -> Dict[str, Any]:
    """
    Retrieve distribution recommendation for an article.

    Args:
        article_id: The article ID

    Returns:
        Dictionary with recommendations, or None if not found
    """
    collection = get_collection("distribution_recommendations")
    return collection.find_one({"article_id": article_id})


def get_articles_by_channel(
    channel: str,
    min_score: float = 0.5,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Find articles recommended for a specific channel.

    Args:
        channel: Distribution channel name
        min_score: Minimum recommendation score
        limit: Maximum number of results

    Returns:
        List of recommendation documents
    """
    collection = get_collection("distribution_recommendations")

    # Query for articles where this channel is recommended with score >= min_score
    cursor = collection.find(
        {
            "recommendations": {
                "$elemMatch": {
                    "channel": channel,
                    "score": {"$gte": min_score}
                }
            }
        }
    ).limit(limit).sort("updated_at", -1)

    return list(cursor)
