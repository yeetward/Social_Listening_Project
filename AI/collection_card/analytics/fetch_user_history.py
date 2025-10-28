from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client["pace_database"]

def get_latest_histories(limit=10):
    """
    Fetch latest search histories
    Returns: List of history objects with subject and metadata
    """
    histories = list(
        db.history.find(
            {"ai_ready": True},  # Only get histories that have AI results
            {
                "subject": 1, 
                "location": 1,
                "industry": 1,
                "created_at": 1, 
                "_id": 1
            }
        ).sort("created_at", -1).limit(limit)
    )
    return histories

def get_top_articles_for_history(history_id, limit=10):
    """
    Get top AI-analyzed articles for a specific history
    Uses the ai_results collection linked by history_id
    """
    articles = list(
        db.ai_results.find(
            {
                "history_id": history_id,
                "status": "done"
            },
            {
                "ai_title": 1,
                "ai_summary": 1,
                "uri": 1,
                "source": 1,
                "relevance_score": 1,
                "published_ts": 1,
                "rank": 1,
                "_id": 0
            }
        ).sort("relevance_score", -1).limit(limit)
    )
    return articles

def build_interest_profile(search_limit=5, articles_per_history=10):
    """
    Build a comprehensive profile based on recent search histories
    """
    recent_histories = get_latest_histories(search_limit)
    
    profile = {
        "search_history": []
    }
    
    for history in recent_histories:
        history_data = {
            "subject": history["subject"],
            "location": history.get("location", "N/A"),
            "industry": history.get("industry", "N/A"),
            "created_at": history["created_at"],
            "history_id": str(history["_id"]),
            "top_articles": get_top_articles_for_history(
                history["_id"], 
                articles_per_history
            )
        }
        profile["search_history"].append(history_data)
    
    return profile