from typing import List, Dict
import requests
from .utils import UA

def fetch(query: str, limit: int = 20) -> List[Dict]:
    params = {
        "query": query or "",
        "tags": "story",
        "hitsPerPage": max(1, min(limit, 50)),
        "restrictSearchableAttributes": "title,url",
    }
    try:
        r = requests.get("https://hn.algolia.com/api/v1/search", params=params, headers=UA, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    hits = data.get("hits", []) or []
    out: List[Dict] = []
    for h in hits:
        url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        title = h.get("title") or ""
        published_ts = h.get("created_at_i") if isinstance(h.get("created_at_i"), int) else None
        author = h.get("author") or ""

        out.append({
            "post_id": f"hackernews_api:{h.get('objectID','')}",
            "source": "hackernews_api",
            "url": url,
            "title": title,
            "text": "",
            "text_html": "",
            "published_ts": published_ts,
            "author": author,
            "engagement": {"points": h.get("points"), "num_comments": h.get("num_comments")},
        })
    return out[:limit]