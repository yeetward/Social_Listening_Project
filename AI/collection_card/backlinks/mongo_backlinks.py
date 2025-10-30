# AI/collection_card/mongo_backlinks.py

from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import MongoClient, UpdateOne
import os

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://AI_Team_Database:46jdJQEZlhoSDagV@cluster0.dqugl74.mongodb.net/pace_database?retryWrites=true&w=majority&appName=Cluster0",
)
client = MongoClient(MONGO_URI)
db = client["pace_database"]


def upsert_backlink_insights(
    company_name: str,
    backlinks: List[Dict[str, Any]],
    history_id: str | None = None,
) -> Tuple[int, int]:
    """
    Store backlink intelligence in MongoDB for dashboard cards.

    We upsert per (company_name, source_url) so we don't duplicate.
    Collection: backlink_insights

    Each doc shaped like:
    {
      company: "...",
      source_url: "...",
      source_domain: "...",
      target_url: "...",
      anchor_text: "...",
      dofollow: true,
      estimated_monthly_clicks: 140,
      domain_authority: 78,
      relevance_score: 0.83,
      sentiment: "positive",
      category: "press",
      ai_summary: "Industry coverage framing us as AI leader.",
      rank: 1,
      history_id: ObjectId(...),
      created_at: ...,
      updated_at: ...
    }
    """
    col = db["backlink_insights"]
    now = datetime.now(timezone.utc)

    ops: List[UpdateOne] = []
    for rank, item in enumerate(backlinks, start=1):
        selector = {"company": company_name, "source_url": item.get("source_url")}

        docset: Dict[str, Any] = {
            "company": company_name,
            "source_url": item.get("source_url"),
            "source_domain": item.get("source_domain"),
            "target_url": item.get("target_url"),
            "anchor_text": item.get("anchor_text"),
            "dofollow": item.get("dofollow"),
            "estimated_monthly_clicks": item.get("estimated_monthly_clicks"),
            "domain_authority": item.get("domain_authority"),
            "relevance_score": item.get("relevance_score"),
            "sentiment": item.get("sentiment"),
            "category": item.get("category"),
            "ai_summary": item.get("ai_summary"),
            "rank": rank,
            "updated_at": now,
        }

        if history_id:
            docset["history_id"] = ObjectId(history_id)

        ops.append(
            UpdateOne(
                selector,
                {"$set": docset, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        )

    result = col.bulk_write(ops) if ops else None
    upserts = getattr(result, "upserted_count", 0) if result else 0
    updates = getattr(result, "modified_count", 0) if result else 0
    return upserts, updates


def get_top_backlinks(company_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Read back top backlinks (already enriched) for frontend dashboard.
    """
    cursor = (
        db["backlink_insights"]
        .find(
            {"company": company_name},
            {
                "_id": 0,
                "source_domain": 1,
                "source_url": 1,
                "relevance_score": 1,
                "sentiment": 1,
                "category": 1,
                "ai_summary": 1,
                "rank": 1,
            },
        )
        .sort("rank", 1)
        .limit(limit)
    )
    return list(cursor)


# from typing import List, Dict, Any, Tuple
# from datetime import datetime, timezone
# from bson import ObjectId
# from pymongo import MongoClient, UpdateOne
# import os

# MONGO_URI = os.getenv(
#     "MONGO_URI",
#     "mongodb+srv://AI_Team_Database:46jdJQEZlhoSDagV@cluster0.dqugl74.mongodb.net/pace_database?retryWrites=true&w=majority&appName=Cluster0",
# )
# client = MongoClient(MONGO_URI)
# db = client["pace_database"]


# def upsert_backlink_insights(
#     company_name: str,
#     backlinks: List[Dict[str, Any]],
#     history_id: str | None = None,
# ) -> Tuple[int, int]:
#     """
#     Store backlink intelligence for dashboard cards.
#     Upsert key: (company, source_url).
#     Collection: backlink_insights
#     """
#     col = db["backlink_insights"]
#     now = datetime.now(timezone.utc)

#     ops: List[UpdateOne] = []
#     for rank, item in enumerate(backlinks, start=1):
#         selector = {"company": company_name, "source_url": item.get("source_url")}
#         docset: Dict[str, Any] = {
#             "company": company_name,
#             "source_url": item.get("source_url"),
#             "source_domain": item.get("source_domain"),
#             "target_url": item.get("target_url"),
#             "anchor_text": item.get("anchor_text"),
#             "dofollow": item.get("dofollow"),
#             "estimated_monthly_clicks": item.get("estimated_monthly_clicks"),
#             "domain_authority": item.get("domain_authority"),
#             "relevance_score": item.get("relevance_score"),
#             "sentiment": item.get("sentiment"),
#             "category": item.get("category"),
#             "ai_summary": item.get("ai_summary"),
#             "rank": rank,
#             "updated_at": now,
#         }
#         if history_id:
#             docset["history_id"] = ObjectId(history_id)

#         ops.append(
#             UpdateOne(
#                 selector,
#                 {"$set": docset, "$setOnInsert": {"created_at": now}},
#                 upsert=True,
#             )
#         )

#     result = col.bulk_write(ops) if ops else None
#     upserts = getattr(result, "upserted_count", 0) if result else 0
#     updates = getattr(result, "modified_count", 0) if result else 0
#     return upserts, updates


# def get_top_backlinks(company_name: str, limit: int = 10) -> List[Dict[str, Any]]:
#     """
#     Read enriched backlinks for the UI.
#     """
#     cursor = (
#         db["backlink_insights"]
#         .find(
#             {"company": company_name},
#             {
#                 "_id": 0,
#                 "source_domain": 1,
#                 "source_url": 1,
#                 "target_url": 1,
#                 "anchor_text": 1,
#                 "relevance_score": 1,
#                 "sentiment": 1,
#                 "category": 1,
#                 "ai_summary": 1,
#                 "rank": 1,
#             },
#         )
#         .sort("rank", 1)
#         .limit(limit)
#     )
#     return list(cursor)
