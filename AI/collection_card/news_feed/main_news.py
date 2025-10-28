from pymongo import MongoClient
import argparse
import analyse_news_relevancy
import json
import fetch_news
import os
import sys

# ---- Mongo Setup ----
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
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


# ---- CLI Entrypoint ----
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run news relevance analysis for a company.")
    parser.add_argument("company_name", type=str, help="Company name (as in MongoDB)")
    parser.add_argument("--news-articles", type=str, help="JSON list of news articles (for manual testing)")
    parser.add_argument("--news-file", type=str, help="Path to JSON file with news articles")
    parser.add_argument("--api-url", type=str, help="HTTPS endpoint to fetch news articles")
    parser.add_argument("--threshold", type=float, default=0.5, help="Minimum relevance threshold (0.0-1.0)")
    parser.add_argument("--limit", type=int, help="Maximum number of articles to return")
    parser.add_argument("--full-analysis", action="store_true", help="Return full analysis with scores")
    parser.add_argument("--verbose", action="store_true", help="Show debug output")
    args = parser.parse_args()

    def log(message):
        """Print to stderr so it doesn't interfere with JSON output"""
        if args.verbose:
            print(message, file=sys.stderr)

    try:
        # Get news articles
        if args.api_url:
            log(f"📡 Fetching news from API...")
            news_articles = fetch_news.get_news_articles(args.api_url)
            log(f"✓ Fetched {len(news_articles)} articles")
        elif args.news_file:
            log(f"📁 Reading news from file: {args.news_file}")
            with open(args.news_file, 'r', encoding='utf-8') as f:
                news_articles = json.load(f)
            if not isinstance(news_articles, list):
                raise ValueError("News articles must be a list of objects.")
            log(f"✓ Loaded {len(news_articles)} articles")
        elif args.news_articles:
            news_articles = json.loads(args.news_articles)
            if not isinstance(news_articles, list):
                raise ValueError("News articles must be a list of objects.")
        else:
            raise ValueError("Must provide either --api-url, --news-file, or --news-articles")

        # Build company context
        log(f"🏢 Building context for {args.company_name}...")
        context = build_context(args.company_name)

        # Run RAG analysis
        log(f"🤖 Analyzing {len(news_articles)} articles...")
        analysis_result = analyse_news_relevancy.news_relevancy_rag(context, news_articles)

        # Filter by threshold
        log(f"🔍 Filtering by threshold {args.threshold}...")
        filtered_results = filter_relevant_news(analysis_result, args.threshold)
        
        # Apply limit if specified
        if args.limit:
            filtered_results = filtered_results[:args.limit]
        
        log(f"✓ {len(filtered_results)} relevant articles found")

        # Prepare output based on flags
        if args.full_analysis:
            output = filtered_results
        else:
            # Return simplified format without internal analysis details
            output = [
                {
                    "title": item["title"],
                    "url": item["url"],
                    "relevance": item["relevance"],
                    "source": item.get("source"),
                    "published_date": item.get("published_date")
                }
                for item in filtered_results
            ]

        # Output clean JSON to stdout
        print(json.dumps(output, indent=2))

    except Exception as e:
        # Print errors to stderr so they don't interfere with JSON output
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)