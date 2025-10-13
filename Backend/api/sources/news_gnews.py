from typing import List, Dict
import requests
from .utils import parse_rss, map_generic_rss_entry

def fetch(query: str, limit: int = 50) -> List[Dict]:
    url = (
        "https://news.google.com/rss/search"
        f"?q={requests.utils.quote(query)}"
        "&hl=en-AU&gl=AU&ceid=AU:en"
    )
    entries = parse_rss(url)
    return [map_generic_rss_entry(e, source_key="news_rss", post_prefix="gnews_rss") for e in entries][:limit]