# Backend/api/persist.py
from typing import Iterable, Tuple
from django.db import transaction
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Source, Post

_url_validator = URLValidator()

def _safe_url(url: str) -> str | None:
    if not url:
        return None
    try:
        _url_validator(url)
        return url
    except ValidationError:
        return None

def _ensure_source(source_key: str, source_name: str | None = None) -> Source:
    # Prefer seeded names, but create if missing
    name = source_name or source_key.replace("_", " ").title()
    src, _ = Source.objects.get_or_create(key=source_key, defaults={"name": name})
    return src

def _epoch_to_dt_utc(ts: int | float | None):
    if not ts:
        return None
    try:
        # guard ms vs sec
        ts = float(ts)
        if ts > 1e12:
            ts = ts / 1000.0
        return timezone.datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except Exception:
        return None

@transaction.atomic
def persist_posts(rows: Iterable[dict]) -> Tuple[int, int]:
    """
    Upsert posts by URL. Returns (created_count, updated_count).
    Expected row shape (matches your fetchers):
      {
        "post_id": str,
        "source": "reddit_rss" | "news_rss" | ...,
        "url": str,
        "title": str,
        "text": str,
        "text_html": str,
        "published_ts": int | None,
        "author": str,
        "engagement": dict | None,
      }
    """
    created, updated = 0, 0

    for p in rows:
        url = _safe_url(p.get("url"))
        if not url:
            # skip invalid/missing URL to avoid DB junk
            continue

        source_key = (p.get("source") or "").strip() or "unknown"
        src = _ensure_source(source_key)

        published_ts = p.get("published_ts")
        published_at = _epoch_to_dt_utc(published_ts)

        defaults = {
            "source": src,
            "post_id": p.get("post_id") or "",
            "title": p.get("title") or "",
            "text": p.get("text") or "",
            "text_html": p.get("text_html") or "",
            "author": p.get("author") or "",
            "published_at": published_at,
            "published_ts": int(published_ts) if isinstance(published_ts, (int, float)) else None,
            "engagement": p.get("engagement"),
        }

        obj, was_created = Post.objects.update_or_create(
            url=url,
            defaults=defaults
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return created, updated
