# # AI/collection_card/mongo_competitors.py
# from __future__ import annotations
# from typing import List, Dict, Any, Tuple
# from datetime import datetime, timezone
# from bson import ObjectId
# from pymongo import MongoClient, UpdateOne
# import os

# MONGO_URI = os.getenv(
#     "MONGO_URI",
#     "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# )
# client = MongoClient(MONGO_URI)
# db = client["pace_database"]

# def upsert_competitor_insights(
#     *,
#     company_id: str,
#     company_name: str,
#     competitors: List[Dict[str, Any]],
#     history_id: str | None = None,
# ) -> Tuple[int, int]:
#     col = db["competitor_insights"]
#     now = datetime.now(timezone.utc)

#     ops: List[UpdateOne] = []
#     for rank, item in enumerate(competitors, start=1):
#         selector = {"company_id": company_id, "competitor": item.get("name")}
#         docset = {
#             "company_id": company_id,
#             "company": company_name,
#             "competitor": item.get("name"),
#             "score": item.get("score"),
#             "signals": item.get("signals"),
#             "explanation": item.get("explanation"),
#             "rank": rank,
#             "updated_at": now,
#         }
#         if history_id:
#             try:
#                 docset["history_id"] = ObjectId(history_id)
#             except Exception:
#                 docset["history_id"] = history_id
#         ops.append(UpdateOne(selector, {"$set": docset, "$setOnInsert": {"created_at": now}}, upsert=True))

#     result = col.bulk_write(ops) if ops else None
#     upserts = getattr(result, "upserted_count", 0) if result else 0
#     updates = getattr(result, "modified_count", 0) if result else 0
#     return upserts, updates


# def get_top_competitors(company_id: str, limit: int = 10) -> List[Dict[str, Any]]:
#     cursor = db["competitor_insights"].find(
#         {"company_id": company_id},
#         {"_id": 0, "competitor": 1, "score": 1, "rank": 1, "explanation": 1}
#     ).sort("rank", 1).limit(limit)

#     out: List[Dict[str, Any]] = []
#     for it in cursor:
#         out.append({
#             "name": it["competitor"],
#             "score": it.get("score", 0.0),
#             "signals": {},
#             "explanation": it.get("explanation", "")
#         })
#     return out
