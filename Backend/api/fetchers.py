# Backend/api/fetchers.py
import time
import re
import html as htmlmod
from typing import List, Dict

import requests
import feedparser
from django.conf import settings

UA = {"User-Agent": "Mozilla/5.0 (compatible; PaceDiscoveryBot/0.1; +http://localhost)"}

# --- helpers ---------------------------------------------------------------

def parse_rss(url: str, timeout: int = 10):
    """Fetch URL with requests (so HTTPS certs work) then parse with feedparser."""
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    feed = feedparser.parse(r.content)
    # if feedparser hit a parsing issue, it sets feed.bozo = True (not fatal)
    return getattr(feed, "entries", []) or []

def _epoch(dt) -> int | None:
    """Convert feedparser's time.struct_time to epoch seconds."""
    if not dt:
        return None
    try:
        return int(time.mktime(dt))
    except Exception:
        return None

TAG_RE = re.compile(r"<[^>]+>")

def clean_html_to_text(html: str) -> str:
    """Very simple HTML→plain-text: unescape entities, strip tags, collapse spaces."""
    if not html:
        return ""
    unescaped = htmlmod.unescape(html)
    no_tags = TAG_RE.sub("", unescaped)
    return " ".join(no_tags.split())

# --- RSS mappers -----------------------------------------------------------

def _map_generic_rss_entry(e, source_key: str, post_prefix: str) -> Dict:
    url = e.get("link") or ""
    title = e.get("title") or ""
    summary_html = (e.get("summary") or "").strip()
    text_plain = clean_html_to_text(summary_html)
    published_ts = _epoch(e.get("published_parsed") or e.get("updated_parsed"))

    # feedparser sometimes gives a nested dict or list for source/author
    author = ""
    src = e.get("source")
    if isinstance(src, dict):
        author = src.get("title") or ""
    author = (e.get("author") or author or "").strip()

    return {
        "post_id": f"{post_prefix}:{hash(url) if url else int(time.time()*1000)}",
        "source": source_key,
        "url": url,
        "title": title,
        "text": text_plain,
        "text_html": summary_html,
        "published_ts": published_ts,
        "author": author,
        "engagement": {
            "score": None,
            "num_comments": None,
            "upvote_ratio": None,
        },
    }

def map_reddit_entry(e) -> Dict:
    return _map_generic_rss_entry(e, source_key="reddit_rss", post_prefix="reddit_rss")

def map_gnews_entry(e) -> Dict:
    # keep the same behavior you had, but via the generic helper
    d = _map_generic_rss_entry(e, source_key="news_rss", post_prefix="gnews_rss")
    return d

# --- fetchers: existing ----------------------------------------------------

def fetch_reddit_rss(subject: str, limit: int = 20) -> List[Dict]:
    url = f"https://www.reddit.com/search.rss?q={requests.utils.quote(subject)}&sort=new"
    entries = parse_rss(url)
    return [map_reddit_entry(e) for e in entries][:limit]

def fetch_reddit_subreddit(sub: str = "technology", limit: int = 20) -> List[Dict]:
    url = f"https://www.reddit.com/r/{sub}/.rss"
    entries = parse_rss(url)
    return [map_reddit_entry(e) for e in entries][:limit]

def fetch_google_news(subject: str, limit: int = 50) -> List[Dict]:
    url = (
        "https://news.google.com/rss/search"
        f"?q={requests.utils.quote(subject)}"
        "&hl=en-AU&gl=AU&ceid=AU:en"
    )
    entries = parse_rss(url)
    return [map_gnews_entry(e) for e in entries][:limit]

# --- NEW: BBC RSS ----------------------------------------------------------

def fetch_bbc_rss(query: str, limit: int = 20) -> List[Dict]:
    """
    BBC global RSS feed + local filtering by query.
    https://feeds.bbci.co.uk/news/rss.xml
    """
    url = "https://feeds.bbci.co.uk/news/rss.xml"
    entries = parse_rss(url)
    q = (query or "").lower().strip()
    out: List[Dict] = []
    for e in entries:
        p = _map_generic_rss_entry(e, source_key="bbc_rss", post_prefix="bbc_rss")
        if q:
            hay = f"{p['title']} {p['text']}".lower()
            if q not in hay:
                continue
        out.append(p)
        if len(out) >= limit:
            break
    return out

# --- NEW: TechCrunch RSS ---------------------------------------------------

def fetch_techcrunch_rss(query: str, limit: int = 20) -> List[Dict]:
    """
    TechCrunch main RSS + local filtering by query.
    https://techcrunch.com/feed/
    """
    url = "https://techcrunch.com/feed/"
    entries = parse_rss(url)
    q = (query or "").lower().strip()
    out: List[Dict] = []
    for e in entries:
        p = _map_generic_rss_entry(e, source_key="techcrunch_rss", post_prefix="techcrunch_rss")
        if q:
            hay = f"{p['title']} {p['text']}".lower()
            if q not in hay:
                continue
        out.append(p)
        if len(out) >= limit:
            break
    return out

# --- NEW: The Guardian API -------------------------------------------------

def fetch_guardian_api(query: str, limit: int = 20) -> List[Dict]:
    """
    Guardian search API (requires GUARDIAN_API_KEY in settings/env).
    Docs: https://open-platform.theguardian.com/documentation/
    """
    api_key = getattr(settings, "GUARDIAN_API_KEY", "") or ""
    if not api_key:
        return []

    params = {
        "api-key": api_key,
        "q": query or "",
        "page-size": max(1, min(limit, 50)),
        "show-fields": "trailText,headline",
    }
    try:
        r = requests.get("https://content.guardianapis.com/search", params=params, headers=UA, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    results = data.get("response", {}).get("results", []) or []
    out: List[Dict] = []
    for it in results:
        url = it.get("webUrl") or ""
        title = (it.get("fields", {}) or {}).get("headline") or it.get("webTitle") or ""
        text_html = (it.get("fields", {}) or {}).get("trailText") or ""
        text_plain = clean_html_to_text(text_html)

        # ISO datetime -> epoch seconds
        published_ts = None
        iso = it.get("webPublicationDate")
        if iso:
            try:
                from datetime import datetime, timezone as dt_tz
                if iso.endswith("Z"):
                    iso = iso[:-1]
                dt = datetime.fromisoformat(iso).replace(tzinfo=dt_tz.utc)
                published_ts = int(dt.timestamp())
            except Exception:
                published_ts = None

        out.append({
            "post_id": f"guardian_api:{it.get('id', '') or hash(url)}",
            "source": "guardian_api",
            "url": url,
            "title": title,
            "text": text_plain,
            "text_html": text_html,
            "published_ts": published_ts,
            "author": it.get("pillarName") or "",
            "engagement": None,
        })

    return out[:limit]

# --- NEW: Hacker News (Algolia) -------------------------------------------

def fetch_hackernews_api(query: str, limit: int = 20) -> List[Dict]:
    """
    Algolia HN Search:
      https://hn.algolia.com/api/v1/search?query=...&tags=story&hitsPerPage=...
    """
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
            "text": "",           # API doesn't return summary
            "text_html": "",
            "published_ts": published_ts,
            "author": author,
            "engagement": {"points": h.get("points"), "num_comments": h.get("num_comments")},
        })
    return out[:limit]