from pymongo import MongoClient
import argparse
import generate_actionable_insights
import json
import os
import sys

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client["pace_database"]

def get_company_context(company_name: str):
    """Get company info from database"""
    company = db.company_profiles.find_one({"name": company_name})
    if not company:
        raise ValueError(f"No company found for {company_name}")
    
    return {
        "company": company["name"],
        "description": company["description"],
        "competitors": company["competitors"]
    }

def get_recent_articles(limit=20):
    """Get most recent analyzed articles"""
    articles = list(
        db.ai_results.find(
            {"status": "done"},
            {
                "ai_title": 1,
                "ai_summary": 1,
                "uri": 1,
                "source": 1,
                "relevance_score": 1,
                "published_ts": 1,
                "_id": 0
            }
        ).sort("created_at", -1).limit(limit)
    )
    return articles

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate actionable insights from recent articles.")
    parser.add_argument("company_name", type=str, help="Company name")
    parser.add_argument("--type", type=str, default="all",
                       choices=["content", "opportunities", "threats", "all"],
                       help="Type of insights to generate")
    parser.add_argument("--limit", type=int, default=20,
                       help="Number of recent articles to analyze")
    parser.add_argument("--verbose", action="store_true", help="Show debug output")
    args = parser.parse_args()

    def log(message):
        if args.verbose:
            print(message, file=sys.stderr)

    try:
        # Get company context
        log(f"🏢 Loading company context for {args.company_name}...")
        company_context = get_company_context(args.company_name)
        
        # Get recent articles
        log(f"📰 Fetching {args.limit} recent articles...")
        recent_articles = get_recent_articles(args.limit)
        log(f"✓ Found {len(recent_articles)} articles")
        
        # Generate insights
        log(f"🤖 Generating {args.type} insights...")
        insights = generate_actionable_insights.generate_actionable_insights(
            company_context,
            recent_articles,
            insight_type=args.type
        )
        
        log(f"✓ Generated {len(insights)} actionable insights")
        
        # Output clean JSON
        print(json.dumps(insights, indent=2))

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)