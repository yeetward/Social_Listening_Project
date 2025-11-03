from bson import ObjectId
from pymongo import MongoClient
import os

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(MONGO_URI)
db = client["pace_database"]

def fetch_articles(history_id: str):
    history_id = ObjectId(history_id)

    queued = list(db.ai_results.find(
        {"history_id": history_id, "status": "queued"},
        {"url": 1, "raw_id": 1, "source": 1, "published_ts": 1}
    ))

    docs = []
    for q in queued:
        raw = db.raw_insights.find_one({"_id": q["raw_id"]}, {"text": 1, "engagement": 1})
        if raw and raw.get("text"):
            docs.append({
                "_id": q["raw_id"],
                "text": raw["text"],
                "engagement": raw.get("engagement", {}),
                "source": q["source"],
                "published_ts": q["published_ts"],
                "url": q["url"],
            })
    return docs