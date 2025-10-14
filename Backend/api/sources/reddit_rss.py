from typing import List, Dict
import requests
from .utils import parse_rss, map_reddit_rss_entry

def fetch(query: str, limit: int = 20) -> List[Dict]:
    url = f"https://www.reddit.com/search.rss?q={requests.utils.quote(query)}&sort=new"
    entries = parse_rss(url)
    return [map_reddit_rss_entry(e) for e in entries][:limit]