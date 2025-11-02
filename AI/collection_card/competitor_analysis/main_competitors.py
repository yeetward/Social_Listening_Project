# # AI/collection_card/main_competitors.py
# from __future__ import annotations
# from typing import List, Dict, Any, Optional
# from pymongo import MongoClient
# import argparse
# import json
# import os
# import sys
# import re

# from .competitor_fusion import extract_competitors
# from .mongo_competitors import upsert_competitor_insights, get_top_competitors

# MONGO_URI = os.getenv(
#     "MONGO_URI",
#     "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# )
# client = MongoClient(MONGO_URI)
# db = client["pace_database"]

# def log(msg: str, verbose: bool):
#     if verbose:
#         print(msg, file=sys.stderr)

# def get_company_context_by_id(company_id: str) -> Dict[str, Any]:
#     """
#     company_profiles:
#     {
#       company_id: str (unique),
#       name: str,
#       created_at: ISODate,
#       description: str,
#       competitors: [str, ...]
#     }
#     """
#     doc = db.company_profiles.find_one({"company_id": company_id})
#     if not doc:
#         raise ValueError(f"No company_profile found for company_id='{company_id}'")
#     return {
#         "company_id": doc["company_id"],
#         "name": doc["name"],
#         "description": doc.get("description", ""),
#         "competitors": doc.get("competitors", []),
#     }

# def get_recent_articles(limit: int = 30, min_relevance: float = 0.3) -> List[Dict[str, Any]]:
#     cursor = db.ai_results.find(
#         {"status": "done", "relevance_score": {"$gte": min_relevance}},
#         {
#             "_id": 0,
#             "ai_title": 1,
#             "ai_summary": 1,
#             "source": 1,
#             "relevance_score": 1,
#             "published_ts": 1,
#         }
#     ).sort([("published_ts", -1), ("relevance_score", -1)]).limit(limit)
#     return list(cursor)

# def get_industry_articles(industry_name: str, limit: int = 30, min_relevance: float = 0.4) -> List[Dict[str, Any]]:
#     """
#     Light industry filter over ai_results. Matches in ai_title, ai_summary, source.
#     """
#     rx = {"$regex": re.escape(industry_name), "$options": "i"}
#     query = {
#         "status": "done",
#         "relevance_score": {"$gte": min_relevance},
#         "$or": [
#             {"ai_title": rx},
#             {"ai_summary": rx},
#             {"source": rx},
#         ]
#     }
#     cursor = db.ai_results.find(
#         query,
#         {
#             "_id": 0,
#             "ai_title": 1,
#             "ai_summary": 1,
#             "source": 1,
#             "relevance_score": 1,
#             "published_ts": 1,
#         }
#     ).sort([("published_ts", -1), ("relevance_score", -1)]).limit(limit)
#     return list(cursor)

# def _articles_to_text_blob(articles: List[Dict[str, Any]]) -> str:
#     parts: List[str] = []
#     for a in articles:
#         title = a.get("ai_title", "") or ""
#         summ  = a.get("ai_summary", "") or ""
#         parts.append(f"{title}. {summ}")
#     return " ".join(parts)

# def run(
#     company_id: str,
#     industry_name: Optional[str] = None,
#     top_n: int = 10,
#     min_score: float = 0.25,
#     limit_articles: int = 30,
#     min_relevance_articles: float = 0.3,
#     persist: bool = False,
#     history_id: Optional[str] = None,
#     verbose: bool = False,
# ) -> List[Dict[str, Any]]:
#     """
#     Returns a competitor list for the given company_id.
#     If industry_name is provided, focuses on that sector; else uses recent relevant articles.
#     """
#     try:
#         ctx = get_company_context_by_id(company_id)
#         seed_brand = ctx["name"]

#         if industry_name:
#             log(f"📰 industry='{industry_name}' → filtered articles", verbose)
#             arts = get_industry_articles(industry_name=industry_name, limit=limit_articles, min_relevance=0.4)
#             industry_tokens = [t for t in re.split(r"\W+", industry_name) if t]
#         else:
#             log("📰 recent high-signal articles", verbose)
#             arts = get_recent_articles(limit=limit_articles, min_relevance=min_relevance_articles)
#             industry_tokens = None

#         text_blob = _articles_to_text_blob(arts)
#         if not text_blob.strip():
#             return []

#         rivals = extract_competitors(
#             text=text_blob,
#             seed_brand=seed_brand,
#             industry=industry_tokens,
#             location=None,
#             top_n=top_n,
#             min_score=min_score,
#         )

#         if persist and rivals:
#             try:
#                 upsert_competitor_insights(
#                     company_id=ctx["company_id"],
#                     company_name=seed_brand,
#                     competitors=rivals,
#                     history_id=history_id,
#                 )
#             except Exception:
#                 # If write perms are blocked, we still return results
#                 pass

#         return rivals

#     except Exception as e:
#         raise RuntimeError(f"competitors.run() failed: {e}") from e

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Return competitor list for a company_id.")
#     parser.add_argument("company_id", type=str, help="Unique company_id from company_profiles")
#     parser.add_argument("--industry-name", type=str, default=None, help="Optional sector/topic filter")
#     parser.add_argument("--top-n", type=int, default=10)
#     parser.add_argument("--min-score", type=float, default=0.25)
#     parser.add_argument("--limit-articles", type=int, default=30)
#     parser.add_argument("--min-relevance-articles", type=float, default=0.3)
#     parser.add_argument("--persist", action="store_true")
#     parser.add_argument("--history-id", type=str, default=None)
#     parser.add_argument("--verbose", action="store_true")
#     args = parser.parse_args()

#     try:
#         out = run(
#             company_id=args.company_id,
#             industry_name=args.industry_name,
#             top_n=args.top_n,
#             min_score=args.min_score,
#             limit_articles=args.limit_articles,
#             min_relevance_articles=args.min_relevance_articles,
#             persist=args.persist,
#             history_id=args.history_id,
#             verbose=args.verbose,
#         )
#         print(json.dumps(out, indent=2))
#     except Exception as e:
#         print(f"ERROR: {e}", file=sys.stderr)
#         sys.exit(1)


# =================



# AI/competitors/main_competitors.py
from __future__ import annotations
from typing import List, Dict, Any
import argparse
import json
import os
import sys
from bson import ObjectId
from pymongo import MongoClient

# Reuse your shared fetcher + optional card writer
from AI.collection_card.fetch_articles import get_company_by_id, get_company_articles
try:
    from AI.collection_card.company_cards import upsert_company_card  # optional
except Exception:
    upsert_company_card = None  # if file not present, we still run

from .competitor_ranker import rank_competitors_from_articles

# --- Mongo (only used to validate a company exists via get_company_by_id) ---
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(MONGO_URI)
db = client["pace_database"]


def log(msg: str, verbose: bool):
    if verbose:
        print(msg, file=sys.stderr)


def run(
    company_id: str,
    *,
    limit_articles: int = 80,
    min_relevance: float = 0.30,
    top_n: int = 10,
    min_score: float = 0.25,
    persist_card: bool = False,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    Programmatic entry point:
      - Pull company profile by ID
      - Pull recent articles for that company
      - Rank & return competitors
      - (optional) save to company_profiles.cards.competitors
    """
    try:
        profile = get_company_by_id(company_id)
        if not profile or not profile.get("name"):
            return []

        company_name = profile["name"]
        log(f"Company: {company_name} ({company_id})", verbose)

        articles = get_company_articles(
            company_id,
            limit=limit_articles,
            min_relevance=min_relevance
        )
        log(f"Articles fetched: {len(articles)}", verbose)

        if not articles:
            return []

        results = rank_competitors_from_articles(
            company_name=company_name,
            articles=articles,
            top_n=top_n,
            min_score=min_score,
        )

        if persist_card and upsert_company_card:
            try:
                payload = {"items": results}
                ok = upsert_company_card(company_id, "competitors", payload)
                log(f"Persisted competitors card: {ok}", verbose)
            except Exception as e:
                # Do not fail the request if write is not permitted
                log(f"(warn) could not persist competitors card: {e}", verbose)

        return results

    except Exception as e:
        raise RuntimeError(f"competitors.run() failed: {e}") from e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate competitor list for a company (by company_id).")
    parser.add_argument("company_id", type=str, help="company_profiles._id (ObjectId string)")
    parser.add_argument("--limit-articles", type=int, default=80, help="max recent articles to consider")
    parser.add_argument("--min-relevance", type=float, default=0.30, help="min relevance_score in ai_results")
    parser.add_argument("--top-n", type=int, default=10, help="max competitors to return")
    parser.add_argument("--min-score", type=float, default=0.25, help="minimum fusion score to keep")
    parser.add_argument("--persist-card", action="store_true", help="save into company_profiles.cards.competitors")
    parser.add_argument("--verbose", action="store_true", help="debug logs to stderr")
    args = parser.parse_args()

    try:
        out = run(
            args.company_id,
            limit_articles=args.limit_articles,
            min_relevance=args.min_relevance,
            top_n=args.top_n,
            min_score=args.min_score,
            persist_card=args.persist_card,
            verbose=args.verbose,
        )
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
