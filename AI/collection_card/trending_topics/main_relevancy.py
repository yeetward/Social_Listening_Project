from pymongo import MongoClient
import argparse
import analyse_relevancy
import json
import fetch_trends
import os
import sys

# ---- Mongo Setup ----
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://AI_Team_Database:46jdJQEZlhoSDagV@cluster0.dqugl74.mongodb.net/pace_database?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client["pace_database"]

# ---- Helpers ----
def get_company_context(company_name: str):
    """Retrieve company description & competitors from Mongo"""
    company = db.company_profiles.find_one({"name": company_name})
    if not company:
        raise ValueError(f"No company found for {company_name}")
    return company["description"], company["competitors"]

def get_recent_searches(limit=10):
    """Retrieve most recent analyzed topics from ai_results (optional)"""
    cursor = db.ai_results.find(
        {"status": "done"},
        {"ai_title": 1, "_id": 0}
    ).sort("published_ts", -1).limit(limit)
    return [doc["ai_title"] for doc in cursor]

def build_context(company_name: str, limit=10):
    """Build internal company context"""
    description, competitors = get_company_context(company_name)
    recent_searches = get_recent_searches(limit)

    context = {
        "company": company_name,
        "description": description,
        "competitors": competitors,
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
    parser.add_argument("company_name", type=str, help="Company name (as in MongoDB)")
    parser.add_argument("--trending-topics", type=str, help="JSON list of trending topics (for manual testing)")
    parser.add_argument("--api-url", type=str, help="HTTPS endpoint to fetch trending topics")
    parser.add_argument("--threshold", type=float, default=0.5, help="Minimum relevance threshold (0.0-1.0)")
    parser.add_argument("--full-analysis", action="store_true", help="Return full analysis with scores instead of just topics")
    parser.add_argument("--verbose", action="store_true", help="Show debug output")
    args = parser.parse_args()

    def log(message):
        """Print to stderr so it doesn't interfere with JSON output"""
        if args.verbose:
            print(message, file=sys.stderr)

    try:
        # Get trending topics
        if args.api_url:
            log(f"📡 Fetching trends from API...")
            trending_topics = fetch_trends.get_trending_topics(args.api_url)
            log(f"✓ Fetched {len(trending_topics)} topics")
        elif args.trending_topics:
            trending_topics = json.loads(args.trending_topics)
            if not isinstance(trending_topics, list):
                raise ValueError("Trending topics must be a list of strings.")
        else:
            raise ValueError("Must provide either --api-url or --trending-topics")

        # Build company context
        log(f"🏢 Building context for {args.company_name}...")
        context = build_context(args.company_name)

        # Run RAG analysis
        log(f"🤖 Analyzing {len(trending_topics)} topics...")
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
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)