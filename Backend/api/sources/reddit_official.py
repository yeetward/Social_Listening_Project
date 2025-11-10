from typing import List, Dict, Optional
import logging
import requests
from django.conf import settings
from .utils import get_reddit_access_token, is_website_url, clean_html_to_text, UA

logger = logging.getLogger(__name__)

def _map(post_data: Dict) -> Optional[Dict]:
    url = post_data.get("url") or f"https://reddit.com{post_data.get('permalink', '')}"
    domain = post_data.get("domain", "")
    if not (domain in ("self.", "reddit.com") or is_website_url(url)):
        logger.debug("Filtered non-website url=%s domain=%s", url, domain)
        return None

    title = post_data.get("title", "")
    text = post_data.get("selftext", "")
    author = post_data.get("author", "")
    created_utc = post_data.get("created_utc")

    engagement = {
        "score": post_data.get("score"),
        "num_comments": post_data.get("num_comments"),
        "upvote_ratio": post_data.get("upvote_ratio"),
        "total_awards": post_data.get("total_awards_received", 0),
    }
    return {
        "post_id": f"reddit_official:{post_data.get('id', '')}",
        "source": "reddit_official",
        "url": url,
        "title": title,
        "text": clean_html_to_text(text),
        "text_html": text,
        "published_ts": int(created_utc) if created_utc else None,
        "author": author,
        "domain": domain,
        "engagement": engagement,
        "is_self_post": domain in ["self.", "reddit.com"],
    }

def fetch(query: str, limit: int = 20) -> List[Dict]:
    token = get_reddit_access_token()
    if not token:
        return []
    headers = {"User-Agent": settings.REDDIT_USER_AGENT, "Authorization": f"Bearer {token}"}
    params = {"q": query, "sort": "new", "limit": min(limit * 3, 100), "type": "link", "restrict_sr": "off"}
    try:
        r = requests.get("https://oauth.reddit.com/search", headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.error("Reddit API error: %s", e)
        return []

    out: List[Dict] = []
    for child in data.get("data", {}).get("children", []):
        post_data = child.get("data", {}) or {}
        mapped = _map(post_data)
        if mapped:
            out.append(mapped)
            if len(out) >= limit:
                break
    return out


