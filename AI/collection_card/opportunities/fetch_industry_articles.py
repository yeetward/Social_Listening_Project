# AI/collection_card/fetch_industry_articles.py

from pymongo import MongoClient
import os
import time

# Mongo connection
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(MONGO_URI)
db = client["pace_database"]


def get_industry_articles(industry_name: str, limit: int = 20, min_relevance: float = 0.4):
    """
    Fetch recent high-relevance articles for a given industry/sector/topic.
    These will be used to generate partnership / growth / expansion opportunities.

    Strategy:
    - Look in ai_results (already AI-enriched with summary, title, relevance_score)
    - Filter:
        * status: "done"
        * relevance_score >= min_relevance
        * ai_title / ai_summary / tags mention the industry_name (simple text match)
    - Sort by recency, then relevance.

    Returns:
        List[dict] of article docs with keys we care about.
    """

    # naive text filter match for now (improve later with embeddings)
    text_match = {"$or": [
        {"ai_title":    {"$regex": industry_name, "$options": "i"}},
        {"ai_summary":  {"$regex": industry_name, "$options": "i"}},
        {"tags":        {"$regex": industry_name, "$options": "i"}},
        {"source":      {"$regex": industry_name, "$options": "i"}},  # fallback
    ]}

    query = {
        "status": "done",
        "relevance_score": {"$gte": min_relevance},
        **text_match
    }

    # if published_ts not always there, fallback to created_at
    cursor = db.ai_results.find(
        query,
        {
            "_id": 0,
            "ai_title": 1,
            "ai_summary": 1,
            "url": 1,
            "source": 1,
            "relevance_score": 1,
            "published_ts": 1,
            "tags": 1,
        }
    ).sort([
        ("published_ts", -1),
        ("relevance_score", -1),
    ]).limit(limit)

    articles = list(cursor)

    # fallback timestamp for missing published_ts (helps LLM context)
    now_ts = int(time.time())
    for art in articles:
        if "published_ts" not in art or art["published_ts"] is None:
            art["published_ts"] = now_ts

    return articles
