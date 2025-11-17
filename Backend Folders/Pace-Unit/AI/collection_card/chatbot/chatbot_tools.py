import sys
import os

# Add parent directory to path so we can import from sibling folders
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from news_feed folder
from news_feed import analyse_news_relevancy
from ideas import generate_actionable_insights

import json
import requests
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client["pace_database"]

def search_and_rank_news(company_name: str, search_query: str, news_api_url: str = None):
    """
    Search for news articles and rank them by relevance to the company
    """
    # Get company context
    company = db.company_profiles.find_one({"name": company_name})
    if not company:
        raise ValueError(f"Company {company_name} not found")
    
    context = {
        "company": company["name"],
        "description": company["description"],
        "competitors": company["competitors"],
        "recent_searches": []
    }
    
    # For now, return mock data (replace with real API later)
    articles = [
        {
            "title": f"Breaking news: {search_query}",
            "description": f"Latest developments in {search_query}",
            "url": "https://example.com/article1",
            "source": "TechNews",
            "published_date": "2025-10-28"
        }
    ]
    
    # Rank using your existing function
    if articles:
        ranked_articles = analyse_news_relevancy.news_relevancy_rag(context, articles)
    else:
        ranked_articles = []
    
    return ranked_articles

def get_insights_for_topic(company_name: str, topic: str, insight_type="all"):
    """
    Search for a topic and generate actionable insights
    """
    # Search and rank
    articles = search_and_rank_news(company_name, topic)
    
    # Filter by relevance
    relevant_articles = [a for a in articles if a.get("relevance", 0) >= 0.5]
    
    if not relevant_articles:
        return {
            "message": f"No highly relevant articles found for '{topic}'",
            "articles_searched": len(articles),
            "relevant_articles": 0,
            "insights": []
        }
    
    # Get company context
    company = db.company_profiles.find_one({"name": company_name})
    company_context = {
        "company": company["name"],
        "description": company["description"],
        "competitors": company["competitors"]
    }
    
    # Generate insights using your existing function
    insights = generate_actionable_insights.generate_actionable_insights(
        company_context,
        relevant_articles,
        insight_type=insight_type
    )
    
    return {
        "topic": topic,
        "articles_searched": len(articles),
        "relevant_articles": len(relevant_articles),
        "insights": insights
    }
