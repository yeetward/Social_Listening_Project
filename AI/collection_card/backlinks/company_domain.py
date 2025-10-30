import os
import re
from urllib.parse import urlparse
from pymongo import MongoClient

_MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://AI_Team_Database:46jdJQEZlhoSDagV@cluster0.dqugl74.mongodb.net/pace_database?retryWrites=true&w=majority&appName=Cluster0",
)
_client = MongoClient(_MONGO_URI)
_db = _client["pace_database"]

_URL_RE = re.compile(r"(https?://[^\s)]+)", re.IGNORECASE)


def extract_domain_from_description(description: str) -> str | None:
    """
    Try to parse a company domain from a URL present in the description text.
    Returns a netloc (e.g., 'roboticmarketer.com') or None.
    """
    if not description:
        return None
    m = _URL_RE.search(description)
    if not m:
        return None
    try:
        netloc = urlparse(m.group(1)).netloc.lower()
        return netloc or None
    except Exception:
        return None


def infer_candidate_domains_from_ai_results(limit: int = 100) -> list[str]:
    """
    Infer likely domains from URLs already seen in ai_results (status='done').
    Useful fallback when description has no explicit URL.
    """
    domains = set()
    cur = (
        _db["ai_results"]
        .find(
            {"status": "done", "url": {"$exists": True, "$ne": None}},
            {"_id": 0, "url": 1},
        )
        .sort("published_ts", -1)
        .limit(limit)
    )
    for row in cur:
        try:
            netloc = urlparse(row["url"]).netloc.lower()
            if netloc:
                domains.add(netloc)
        except Exception:
            continue
    return sorted(domains)
