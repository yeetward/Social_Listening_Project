# Backend/api/fetchers.py
import time
import re
import html as htmlmod
from typing import List, Dict

import requests
import feedparser

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

# --- mappers ---------------------------------------------------------------

def map_reddit_entry(e) -> Dict:
    # works for search.rss and subreddit .rss
    url = e.get("link") or ""
    title = e.get("title") or ""
    summary_html = (e.get("summary") or "").strip()
    text_plain = clean_html_to_text(summary_html)
    published_ts = _epoch(e.get("published_parsed") or e.get("updated_parsed"))
    author = (e.get("author") or "").strip()
    post_id = f"reddit_rss:{hash(url)}"

    return {
        "post_id": post_id,
        "source": "reddit_rss",
        "url": url,
        "title": title,
        "text": text_plain,        # plain text for AI
        "text_html": summary_html, # original HTML for FE if needed
        "published_ts": published_ts,
        "author": author,
        # optional engagement shape (placeholders for now)
        "engagement": {
            "score": None,
            "num_comments": None,
            "upvote_ratio": None,
        },
    }

def map_gnews_entry(e) -> Dict:
    url = e.get("link") or ""
    title = e.get("title") or ""
    summary_html = (e.get("summary") or "").strip()
    text_plain = clean_html_to_text(summary_html)
    published_ts = _epoch(e.get("published_parsed") or e.get("updated_parsed"))
    # feedparser sometimes gives a nested dict for source
    src = e.get("source")
    author = (src.get("title") if isinstance(src, dict) else "") or ""
    post_id = f"gnews_rss:{hash(url)}"

    return {
        "post_id": post_id,
        "source": "news_rss",
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

# --- fetchers --------------------------------------------------------------

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
