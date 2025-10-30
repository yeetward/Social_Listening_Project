from pymongo import MongoClient
import sys
from bson import ObjectId
import os
from . import analyse_relevancy
from . import fetch_trends

# ---- Mongo Setup ----
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://AI_Team_Database:46jdJQEZlhoSDagV@cluster0.dqugl74.mongodb.net/pace_database?retryWrites=true&w=majority&appName=Cluster0")
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

def run(company_id: str):
    """
    Main callable entry point for backend integration.
    Equivalent to running this file as a CLI.
    Returns a Python list — either:
      - list[str] of topic names (if full_analysis=False)
    """

    api_url = "http://127.0.0.1:8001/api/trends/"
    try:
        #Fetch trending topics
        trending_topics = fetch_trends.get_trending_topics(api_url)
        if not trending_topics:
            raise ValueError("No trending topics retrieved")

        # Build company context
        context = build_context(company_id)

        # Run AI relevance analysis
        analysis_result = analyse_relevancy.relevancy_rag(context, trending_topics)
 
        return analysis_result

    except Exception as e:
        raise RuntimeError(f"run() failed: {e}")
    