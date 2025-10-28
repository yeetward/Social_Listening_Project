import requests
import sys

def get_trending_topics(api_url=None, verbose=False):
    """
    Fetch trending topics from an API endpoint
    Args:
        api_url: The HTTPS endpoint URL
        verbose: Show debug output
    Returns:
        list: List of trending topic strings
    """
    if not api_url:
        raise ValueError("API URL not provided")
    
    try:
        if verbose:
            print(f"📡 Fetching trends from: {api_url}", file=sys.stderr)
        
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle different response formats
        if isinstance(data, list):
            trending_topics = data
        elif isinstance(data, dict) and "trends" in data:
            trending_topics = data["trends"]
        elif isinstance(data, dict) and "topics" in data:
            trending_topics = data["topics"]
        else:
            raise ValueError(f"Unexpected response format: {data}")
        
        if verbose:
            print(f"✓ Fetched {len(trending_topics)} trending topics", file=sys.stderr)
        
        return trending_topics
        
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch trends: {e}")