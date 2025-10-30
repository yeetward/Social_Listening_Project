from pymongo import MongoClient
from . import analyse_news_relevancy
from . import fetch_news
import os
from bson import ObjectId
import sys


# ---- Mongo Setup ----
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client["pace_database"]

# ---- Helpers ----
def get_company_context(company_id: str):
    """Retrieve company description & competitors from Mongo by ID"""
    try:
        # Convert string ID to ObjectId
        obj_id = ObjectId(company_id)
    except Exception as e:
        raise ValueError(f"Invalid company ID format: {company_id}")
    
    company = db.company_profiles.find_one({"_id": obj_id})
    if not company:
        raise ValueError(f"No company found for ID {company_id}")
    
    return {
        "name": company["name"],
        "description": company["description"],
        "competitors": company["competitors"]
    }

def build_context(company_id: str, limit=10):
    """Build internal company context"""
    company_info = get_company_context(company_id)

    context = {
        "company": company_info["name"],
        "description": company_info["description"],
        "competitors": company_info["competitors"],
    }
    return context

def filter_relevant_news(analysis_result: list, threshold=0.5):
    """
    Filter news articles by relevance threshold
    Args:
        analysis_result: List of dicts with article data and 'relevance'
        threshold: Minimum relevance score (0.0 to 1.0)
    Returns:
        List of relevant articles with metadata
    """
    relevant_news = [
        item 
        for item in analysis_result 
        if item.get("relevance", 0) >= threshold
    ]
    return relevant_news

def run(company_id: str):
    """
    Programmatic entrypoint equivalent to CLI.
    Fetches, analyzes, and filters news relevant to a given company.
    """
    api_url = None
    try:
        articles = fetch_news.get_news_articles(api_url)

        # 2. Build company context
        context = build_context(company_id)

        # 3. Run RAG analysis
        analysis_result = analyse_news_relevancy.news_relevancy_rag(context, articles)
        return analysis_result



    except Exception as e:
        raise RuntimeError(f"newsfeed.run() failed: {e}") from e
    