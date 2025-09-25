# Backend/api/fetchers.py
import time
import re
import html as htmlmod
from typing import List, Dict

import base64
import logging
logger = logging.getLogger(__name__)

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
# --- Official reddit ----------------------------------------------------
def _is_website_url(url: str) -> bool:
    """
    Check if URL points to a website (article, blog, news, etc.)
    and not media (images, videos, Reddit galleries, etc.)
    """
    if not url:
        return False
    
    # Common media file extensions to exclude
    media_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg',
        '.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv', '.wmv',
        '.mp3', '.wav', '.ogg', '.m4a', '.flac',
    }
    
    # Check file extension first
    if any(url.lower().endswith(ext) for ext in media_extensions):
        return False
    
    # Common media hosting domains to exclude
    media_domains = {
        'i.redd.it',      # Reddit images
        'v.redd.it',      # Reddit videos
        'reddit.com/gallery/',  # Reddit galleries
        'imgur.com',      # Imgur
        'giphy.com',      # Giphy
        'gfycat.com',     # Gfycat
        'streamable.com', # Streamable
    }
    
    from urllib.parse import urlparse
    parsed = urlparse(url.lower())
    domain = parsed.netloc
    path = parsed.path
    
    # Check if domain is a media host
    for media_domain in media_domains:
        if media_domain in domain:
            return False
    
    # SPECIAL CASE: Reddit URLs - we want to keep text posts but filter media
    if domain in ['reddit.com', 'www.reddit.com']:
        # Allow Reddit text posts (subreddit discussions)
        if '/r/' in path and '/comments/' in path:
            return True
        # Filter out other Reddit media
        return False
    
    # Allow common website domains
    website_domains = {
        'reddit.com', 'www.reddit.com',
        'youtube.com', 'youtu.be',        # Allow YouTube (often has educational content)
        'vimeo.com',                      # Allow Vimeo (educational/creative)
        'medium.com', 'substack.com',     # Blog platforms
        'github.com', 'gitlab.com',       # Code repositories
        'twitter.com', 'x.com',           # Social media (often shares articles)
        'linkedin.com',                   # Professional content
        # News sites
        'nytimes.com', 'washingtonpost.com', 'theguardian.com',
        'bbc.com', 'reuters.com', 'apnews.com', 'bloomberg.com',
        'techcrunch.com', 'wired.com', 'theverge.com', 'arstechnica.com',
        # Blog platforms
        'wordpress.com', 'blogspot.com', 'tumblr.com',
    }
    
    # If it's a known website domain, allow it
    for website_domain in website_domains:
        if website_domain in domain:
            return True
    
    # For unknown domains, use a more permissive approach
    # Allow anything that doesn't look like media
    if '.' not in domain:  # Probably not a real website
        return False
        
    # If it has a common TLD and doesn't look like media, allow it
    common_tlds = {'.com', '.org', '.net', '.edu', '.gov', '.io', '.co'}
    if any(domain.endswith(tld) for tld in common_tlds):
        return True
    
    return False

def _is_reddit_self_post(url: str) -> bool:
    """Check if URL is a Reddit self-post (text content)"""
    if not url:
        return False
    
    from urllib.parse import urlparse
    parsed = urlparse(url.lower())
    domain = parsed.netloc
    
    return domain in ['reddit.com', 'www.reddit.com'] and '/r/' in parsed.path and '/comments/' in parsed.path

def fetch_reddit_official(subject: str, limit: int = 20) -> List[Dict]:
    """Official Reddit API search for website content only"""
    access_token = _get_reddit_access_token()
    if not access_token:
        return []

    headers = {
        "User-Agent": settings.REDDIT_USER_AGENT,
        "Authorization": f"Bearer {access_token}"
    }

    try:
        url = f"https://oauth.reddit.com/search"
        params = {
            "q": subject,
            "sort": "new",
            "limit": min(limit * 3, 100),  # Get more to account for filtering
            "type": "link",
            "restrict_sr": "off"  # Search all subreddits
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        posts = []
        for child in data.get("data", {}).get("children", []):
            post_data = child.get("data", {})
            if not post_data:
                continue
                
            mapped = _map_reddit_official_post(post_data)
            if mapped:  # Only add if it's website content
                posts.append(mapped)
                if len(posts) >= limit:
                    break
            
        return posts
        
    except Exception as e:
        logger.error(f"Reddit API error: {e}")
        return []

def _get_reddit_access_token() -> str | None:
    """Get OAuth2 access token for Reddit API"""
    try:
        auth_str = f"{settings.REDDIT_CLIENT_ID}:{settings.REDDIT_CLIENT_SECRET}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        
        headers = {
            "User-Agent": settings.REDDIT_USER_AGENT,
            "Authorization": f"Basic {encoded_auth}"
        }
        
        data = {
            "grant_type": "client_credentials"
        }
        
        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            headers=headers,
            data=data,
            timeout=10
        )
        response.raise_for_status()
        
        return response.json().get("access_token")
        
    except Exception as e:
        logger.error(f"Reddit token error: {e}")
        return None

def _map_reddit_official_post(post_data: Dict) -> Dict | None:
    """Map Reddit API response, be smarter about website detection"""
    
    url = post_data.get("url") or f"https://reddit.com{post_data.get('permalink', '')}"
    domain = post_data.get("domain", "")
    
    # For Reddit self-posts (text content), always include them
    if domain == "self." or domain == "reddit.com":
        # This is a Reddit text post - good content
        pass
    else:
        # For external links, check if it's website content
        if not _is_website_url(url):
            print(f"DEBUG: Filtered out non-website: {url} (domain: {domain})")
            return None
    
    title = post_data.get("title", "")
    text = post_data.get("selftext", "")
    author = post_data.get("author", "")
    created_utc = post_data.get("created_utc")
    
    engagement = {
        "score": post_data.get("score"),
        "num_comments": post_data.get("num_comments"),
        "upvote_ratio": post_data.get("upvote_ratio"),
        "total_awards": post_data.get("total_awards_received", 0)
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