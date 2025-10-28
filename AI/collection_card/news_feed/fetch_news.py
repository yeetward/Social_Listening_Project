import requests
import sys

def get_news_articles(api_url=None, verbose=False):
    """
    Fetch news articles from an API endpoint
    Args:
        api_url: The HTTPS endpoint URL
        verbose: Show debug output
    Returns:
        list: List of news article dictionaries with 'title', 'description', 'url', etc.
    """
    if not api_url:
        raise ValueError("API URL not provided")
    
    try:
        if verbose:
            print(f"📡 Fetching news from: {api_url}", file=sys.stderr)
        
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle different response formats
        if isinstance(data, list):
            news_articles = data
        elif isinstance(data, dict) and "articles" in data:
            news_articles = data["articles"]
        elif isinstance(data, dict) and "news" in data:
            news_articles = data["news"]
        elif isinstance(data, dict) and "data" in data:
            news_articles = data["data"]
        else:
            raise ValueError(f"Unexpected response format: {data}")
        
        # Validate article structure
        required_fields = ["title"]
        for article in news_articles:
            if not isinstance(article, dict):
                raise ValueError(f"Each article must be a dictionary, got {type(article)}")
            if not any(field in article for field in required_fields):
                raise ValueError(f"Each article must have at least a 'title' field")
        
        if verbose:
            print(f"✓ Fetched {len(news_articles)} news articles", file=sys.stderr)
        
        return news_articles
        
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch news: {e}")