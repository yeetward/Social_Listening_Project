from pymongo import MongoClient
import argparse
import analyse_relevancy
import json
import sys
from bson import ObjectId
import os
import fetch_trends

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

def get_recent_searches(limit=10):
    """Retrieve most recent analyzed topics from ai_results (optional)"""
    cursor = db.ai_results.find(
        {"status": "done"},
        {"ai_title": 1, "_id": 0}
    ).sort("published_ts", -1).limit(limit)
    return [doc["ai_title"] for doc in cursor]

def build_context(company_id: str, limit=10):
    """Build internal company context"""
    company_info = get_company_context(company_id)
    recent_searches = get_recent_searches(limit)

    context = {
        "company": company_info["name"],
        "description": company_info["description"],
        "competitors": company_info["competitors"],
        "recent_searches": recent_searches
    }
    return context

def filter_relevant_topics(analysis_result: list, threshold=0.5):
    """
    Filter topics by relevance threshold and return just topic names
    Args:
        analysis_result: List of dicts with 'topic' and 'relevance'
        threshold: Minimum relevance score (0.0 to 1.0)
    Returns:
        List of relevant topic names
    """
    relevant_topics = [
        item["topic"] 
        for item in analysis_result 
        if item.get("relevance", 0) >= threshold
    ]
    return relevant_topics

# ---- CLI Entrypoint ----
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run topic relevance RAG for a company.")
    parser.add_argument("company_id", type=str, help="Company ID (MongoDB ObjectId)")
    parser.add_argument("--api-url", type=str, 
                        default="http://127.0.0.1:8001/api/trends/",
                        help="API endpoint for trending topics")
    parser.add_argument("--full-analysis", action="store_true",
                        help="Return full analysis with scores instead of just topic names")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="Minimum relevance threshold (0.0-1.0, default: 0.5)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show debug output")

    args = parser.parse_args()

    try:
        # Fetch trending topics from API
        trending_topics = fetch_trends.get_trending_topics(args.api_url, verbose=args.verbose)
        
        if not trending_topics:
            print("Error: No trending topics retrieved", file=sys.stderr)
            sys.exit(1)
        
        # Build company context
        context = build_context(args.company_id)

        # Run RAG analysis
        analysis_result = analyse_relevancy.relevancy_rag(context, trending_topics)

        # Prepare output based on flags
        if args.full_analysis:
            # Return full analysis with scores
            output = analysis_result
        else:
            # Return only relevant topic names
            output = filter_relevant_topics(analysis_result, args.threshold)

        # Output clean JSON to stdout (backend can parse this)
        print(json.dumps(output))

    except Exception as e:
        # Print errors to stderr so they don't interfere with JSON output
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)