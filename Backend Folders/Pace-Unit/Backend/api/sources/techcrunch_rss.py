from typing import List, Dict
from .utils import parse_rss, map_generic_rss_entry

def fetch(query: str, limit: int = 20) -> List[Dict]:
    url = "https://techcrunch.com/feed/"
    entries = parse_rss(url)
    q = (query or "").lower().strip()
    out: List[Dict] = []
    for e in entries:
        p = map_generic_rss_entry(e, source_key="techcrunch_rss", post_prefix="techcrunch_rss")
        if q:
            hay = f"{p['title']} {p['text']}".lower()
            if q not in hay:
                continue
        out.append(p)
        if len(out) >= limit:
            break
    return out