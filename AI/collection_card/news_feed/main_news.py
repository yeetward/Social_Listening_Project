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

#def run(company_id: str):
def run(
    company_name: str,
    api_url: str | None = None,
    api_key: str | None = None,
    limit: int = 50,
    no_llm: bool = False,
    history_id: str | None = None,
    return_stored: bool = False,
    verbose: bool = False,
):
    """
    Programmatic entrypoint equivalent to CLI.
    Fetches, analyzes, and filters news relevant to a given company.
    """
    api_url = None
    try:
        # articles = fetch_news.get_news_articles(api_url)
        dummy_response = {
    "articles": [
        {
            "title": "EV Motors Launches New Range of Affordable Electric Vehicles",
            "description": "EV Motors unveiled its new 'EcoDrive' series aimed at making electric mobility accessible to all consumers.",
            "url": "https://example.com/evmotors-ecodrive-launch",
            "author": "Jane Doe",
            "source": "TechNews Daily",
            "publishedAt": "2025-10-30T08:00:00Z"
        },
        {
            "title": "EV Motors Partners with SolarGrid for Sustainable Charging Network",
            "description": "The partnership will enable EV owners to charge using 100% renewable solar energy at over 500 new stations nationwide.",
            "url": "https://example.com/evmotors-solargrid-partnership",
            "author": "John Smith",
            "source": "GreenFuture Magazine",
            "publishedAt": "2025-10-29T14:30:00Z"
        },
        {
            "title": "EV Motors Reports Record Quarterly Sales Amid Growing EV Adoption",
            "description": "Strong demand for electric SUVs and compact cars has pushed EV Motors’ revenue up by 25% compared to last year.",
            "url": "https://example.com/evmotors-q3-sales",
            "author": "Emily Nguyen",
            "source": "Reuters",
            "publishedAt": "2025-10-27T10:15:00Z"
        }
    ]
}


        # 2. Build company context
        context = build_context("68feebb67c33c037fd2d62f7")

        # 3. Run RAG analysis
        analysis_result = analyse_news_relevancy.news_relevancy_rag(context, articles)
        return analysis_result


    except Exception as e:
        raise RuntimeError(f"newsfeed.run() failed: {e}") from e
    