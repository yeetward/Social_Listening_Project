from typing import List, Dict, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import UpdateOne, MongoClient

MONGO_URI = "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["pace_database"]


def get_engagement_by_history_id(history_id):
    """
    Returns engagement data from raw_insights for all ai_results linked to a given history_id
    """
    try:
        # Step 1: Find ai_results linked to the history_id
        ai_results = list(db.ai_results.find({"history_id": ObjectId(history_id)}))
        if not ai_results:
            return f"No AI results found for history_id: {history_id}"

        engagements = []

        # Step 2: For each ai_result, find the corresponding raw_insight document
        for result in ai_results:
            raw_id = result.get("raw_id")
            if raw_id:
                raw_doc = db.raw_insights.find_one({"_id": raw_id}, {"engagement": 1, "url": 1, "source": 1})
                if raw_doc and "engagement" in raw_doc:
                    engagements.append({
                        "url": raw_doc.get("url"),
                        "source": raw_doc.get("source"),
                        "engagement": raw_doc["engagement"]
                    })

        # Step 3: Return engagement details
        if not engagements:
            return f"No engagement data found for history_id: {history_id}"

        return engagements

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    history_id = "68fdda1caf9de874acb5a32a"
    engagement_data = get_engagement_by_history_id(history_id)
    for e in engagement_data:
        print(e)

