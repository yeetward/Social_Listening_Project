import time
import re
import html as htmlmod
import base64
import logging
from typing import Dict, List, Optional
import requests
import feedparser
from django.conf import settings

logger = logging.getLogger(__name__)

UA = {"User-Agent": "Mozilla/5.0 (compatible; PaceDiscoveryBot/0.1; +http://localhost)"}

# helpers 

def parse_rss(url: str, timeout: int = 10):
    """Fetch URL with requests (so HTTPS certs work) then parse with feedparser."""
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    feed = feedparser.parse(r.content)
    return getattr(feed, "entries", []) or []

def epoch(dt) -> Optional[int]:
    """Convert feedparser's time.struct_time to epoch seconds."""
    if not dt:
        return None
    try:
        return int(time.mktime(dt))
    except Exception:
        return None

_TAG_RE = re.compile(r"<[^>]+>")

def clean_html_to_text(html: str) -> str:
    """Very simple HTML→plain-text: unescape entities, strip tags, collapse spaces."""
    if not html:
        return ""
    unescaped = htmlmod.unescape(html)
    no_tags = _TAG_RE.sub("", unescaped)
    return " ".join(no_tags.split())

def is_website_url(url: str) -> bool:
    """
    Return True for article/blog/news/etc. URLs; False for media (images/videos/galleries).
    """
    if not url:
        return False

    media_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg',
        '.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv', '.wmv',
        '.mp3', '.wav', '.ogg', '.m4a', '.flac',
    }
    if any(url.lower().endswith(ext) for ext in media_extensions):
        return False

    media_domains = {
        'i.redd.it', 'v.redd.it', 'reddit.com/gallery/', 'imgur.com',
        'giphy.com', 'gfycat.com', 'streamable.com',
    }
    from urllib.parse import urlparse
    parsed = urlparse(url.lower())
    domain = parsed.netloc
    path = parsed.path

    for m in media_domains:
        if m in domain:
            return False

    if domain in ['reddit.com', 'www.reddit.com']:
        if '/r/' in path and '/comments/' in path:
            return True
        return False

    website_domains = {
        'reddit.com', 'www.reddit.com',
        'youtube.com', 'youtu.be', 'vimeo.com',
        'medium.com', 'substack.com',
        'github.com', 'gitlab.com',
        'twitter.com', 'x.com', 'linkedin.com',
        'nytimes.com', 'washingtonpost.com', 'theguardian.com',
        'bbc.com', 'reuters.com', 'apnews.com', 'bloomberg.com',
        'techcrunch.com', 'wired.com', 'theverge.com', 'arstechnica.com',
        'wordpress.com', 'blogspot.com', 'tumblr.com',
    }
    for w in website_domains:
        if w in domain:
            return True

    if '.' not in domain:
        return False

    common_tlds = {'.com', '.org', '.net', '.edu', '.gov', '.io', '.co'}
    if any(domain.endswith(tld) for tld in common_tlds):
        return True

    return False

# mappers 

def map_generic_rss_entry(e, source_key: str, post_prefix: str) -> Dict:
    url = e.get("link") or ""
    title = e.get("title") or ""
    summary_html = (e.get("summary") or "").strip()
    text_plain = clean_html_to_text(summary_html)
    published_ts = epoch(e.get("published_parsed") or e.get("updated_parsed"))

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

def map_reddit_rss_entry(e) -> Dict:
    return map_generic_rss_entry(e, source_key="reddit_rss", post_prefix="reddit_rss")

# reddit oauth 

def get_reddit_access_token() -> Optional[str]:
    try:
        auth_str = f"{settings.REDDIT_CLIENT_ID}:{settings.REDDIT_CLIENT_SECRET}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        headers = {"User-Agent": settings.REDDIT_USER_AGENT, "Authorization": f"Basic {encoded_auth}"}
        data = {"grant_type": "client_credentials"}
        r = requests.post("https://www.reddit.com/api/v1/access_token", headers=headers, data=data, timeout=10)
        r.raise_for_status()
        return r.json().get("access_token")
    except Exception as e:
        logger.error("Reddit token error: %s", e)
        return None