from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

import requests
from datetime import datetime, timezone, timedelta

from .persist import _iso_z, get_mongo_db, get_company_profile

import logging, time, json
import re 
from bson import ObjectId
from threading import Thread

from .analytics import trend_timeseries_by_day, trend_top_tags, trend_by_source, _parse_iso_to_date, _coerce_topics_list
from .analytics import global_top_topics
from .analytics import _as_list

from .sources import REGISTRY as FETCHERS
from .persist import (
    get_mongo_db,
    create_history,
    persist_raw_insights,
    seed_ai_result_stubs,
    get_company_profile,
    mark_history_ai_started,
    mark_history_ai_progress,
    mark_history_ai_done,
    write_ai_results_batch,
)

logger = logging.getLogger(__name__)



# NewsAPI config (for news_feed only)
NEWSAPI_DEFAULT_KEY = "11da17e92c5d487f874c914347697aec"  
NEWSAPI_ENDPOINT = "https://newsapi.org/v2/everything"

# def _to_bool(v, default=False):
#     if v is None:
#         return default
#     s = str(v).strip().lower()
#     return s in ("1", "true", "yes", "y", "on")

# def _epoch_to_iso_z(ts):
#     """Convert unix seconds -> ISO8601 Z string; returns None if bad."""
#     try:
#         return datetime.fromtimestamp(int(ts), tz=timezone.utc) \
#                        .isoformat().replace("+00:00", "Z")
#     except Exception:
#         return None

def _map_newsapi_articles(articles):
    """
    Map NewsAPI articles to the AI-expected schema:
    {title, description, url, author, source, publishedAt}
    """
    mapped = []
    for a in (articles or []):
        source_name = None
        src = a.get("source")
        if isinstance(src, dict):
            source_name = src.get("name")
        if not source_name:
            source_name = src if isinstance(src, str) else "Unknown"

        mapped.append({
            "title": a.get("title") or "",
            "description": a.get("description") or "",
            "url": a.get("url") or "",
            "author": a.get("author") or None,
            "source": source_name,
            "publishedAt": a.get("publishedAt"),  # keep NewsAPI ISO string
        })
    return mapped


def _fetch_from_newsapi(query: str, api_key: str, page_size: int = 50):
    params = {
        "q": query,
        "pageSize": max(10, min(int(page_size), 100)),
        "language": "en",
        "sortBy": "publishedAt",
        "apiKey": api_key,
    }
    r = requests.get(NEWSAPI_ENDPOINT, params=params, timeout=25)
    r.raise_for_status()
    payload = r.json()
    return _map_newsapi_articles(payload.get("articles") or [])

# ---------------------------------------------------------------------
# SerpAPI (Google Trends) config (for card_trends)
# ---------------------------------------------------------------------
SERPAPI_DEFAULT_KEY = "62aef6d6cf4760d45568f2b6483029d361df42eff443ebbffe7063cb594ce6a3"  # demo key (user approved to expose)
SERPAPI_ENDPOINT    = "https://serpapi.com/search.json"

URL_RE = re.compile(r'https?://', re.I)

def _sanitize_topics(seq: list[str], *, max_len: int = 60) -> list[str]:
    """
    Keep only clean, short, non-URL, human topics.
    Dedupe case-insensitively.
    """
    out, seen = [], set()

    for s in (seq or []):
        if not isinstance(s, str):
            continue

        # Normalize spacing
        s = " ".join(s.strip().split())
        if not s:
            continue

        # Remove URL-like strings
        if URL_RE.search(s):
            continue

        # Length guard
        if len(s) < 2 or len(s) > max_len:
            continue

        # Must contain at least one letter (drop pure symbols, numbers)
        if not re.search(r"[A-Za-z]", s):
            continue

        # ✅ NEW RULE: Drop base64/page-token looking junk
        # e.g. "mAGHz3ica1xTlFpYmlpcEp-SWJ..."
        if " " not in s and len(s) >= 16 and re.match(r"^[A-Za-z0-9_\-]+$", s):
            continue

        # Deduplicate case-insensitively
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)

        out.append(s)

    return out


def _serpapi_date_for_days(days: int) -> str:
    """
    Map a days window to Google Trends 'date' values.
    """
    try:
        d = int(days)
    except Exception:
        d = 30
    if d <= 7:   return "now 7-d"
    if d <= 30:  return "today 1-m"
    if d <= 90:  return "today 3-m"
    return "today 12-m"

def _coerce_topic_strings(obj, acc: set):
    """
    Traverse dict/list and collect plausible topic strings.
    Avoids URL-like strings and junk tokens.
    """
    if obj is None:
        return
    if isinstance(obj, str):
        s = " ".join(obj.strip().split())
        if s and not URL_RE.search(s) and re.search(r"[A-Za-z]", s):
            acc.add(s)
        return
    if isinstance(obj, list):
        for it in obj:
            _coerce_topic_strings(it, acc)
        return
    if isinstance(obj, dict):
        # Prefer common keys first
        for k in ("topic", "topic_title", "title", "query", "name", "keyword"):
            v = obj.get(k)
            if isinstance(v, str):
                s = " ".join(v.strip().split())
                if s and not URL_RE.search(s) and re.search(r"[A-Za-z]", s):
                    acc.add(s)
        # Also traverse down
        for v in obj.values():
            _coerce_topic_strings(v, acc)


def _fetch_trending_topics_serpapi(query: str | None, *, geo: str = "AU", days: int = 30, limit: int = 30, api_key: str = SERPAPI_DEFAULT_KEY) -> list[str]:
    """
    If query is provided: use Google Trends 'related topics' for that query.
    Else: use 'trending now' for the region (geo).
    Returns a de-duplicated list[str] topics, trimmed to 'limit'.
    """
    import requests

    topics: set[str] = set()

    if (query or "").strip():
        # Related topics for a specific query
        params = {
            "engine": "google_trends",
            "q": query.strip(),
            "data_type": "RELATED_TOPICS",         # ask for related topics
            "date": _serpapi_date_for_days(days),  # e.g., "today 1-m"
            "geo": geo or "AU",
            "api_key": api_key,
        }
        try:
            r = requests.get(SERPAPI_ENDPOINT, params=params, timeout=25)
            r.raise_for_status()
            payload = r.json() or {}
            # Extract aggressively from the payload
            _coerce_topic_strings(payload.get("related_topics"), topics)
            # Fallback: related queries often present when related topics are thin
            _coerce_topic_strings(payload.get("related_queries"), topics)
        except Exception:
            # fall through to trending-now as a backup
            pass

    # If no query OR above returned too little, use trending-now for the region
    if not topics:
        params = {
            "engine": "google_trends_trending_now",
            "geo": geo or "AU",
            "api_key": api_key,
        }
        try:
            r = requests.get(SERPAPI_ENDPOINT, params=params, timeout=25)
            r.raise_for_status()
            payload = r.json() or {}
            _coerce_topic_strings(payload.get("trending_searches"), topics)
        except Exception:
            # final fallback: empty
            pass

    out = [t for t in topics if t][:limit]
    return out

# -----------------------------------------------------------------------------
# Optional AI imports
# -----------------------------------------------------------------------------
try:
    from AI.ranking_algorithm.main import run as external_ai_run
except Exception as e:
    external_ai_run = None
    logger.exception("Failed to import AI.ranking_algorithm.main.run: %s", e)


# Company-aware News analyzer (optional)
try:
    from AI.collection_card.news_feed import analyse_news_relevancy
except Exception:
    analyse_news_relevancy = None
    logger.warning("AI.collection_card.news_feed.analyse_news_relevancy not importable.")


try:
    from AI.collection_card.trending_topics.main_relevancy import run as trending_run
except Exception as e:
    trending_run = None
    logger.warning("Failed to import trending run(): %s", e)



try:
    from AI.collection_card.ideas.main_ideas import run as ideas_run
except Exception as e:
    ideas_run = None
    logger.warning("Failed to import ideas.run(): %s", e)


try:
    from AI.collection_card.competitor_analysis.main_competitors import run as competitors_run
except Exception as e:
    competitor_run = None
    logger.warning("Failed to import competitor_fusion_demo.run(): %s", e)

try:
    from AI.collection_card.backlinks.main_backlinks import run as backlinks_run
except Exception as e:
    backlinks_run = None
    logger.warning("Failed to import backlinks.run(): %s", e)

try:
    from AI.collection_card.opportunities.main_opportunities import run as opportunities_run
except Exception as e:
    opportunities_run = None
    logger.warning("Failed to import opportunities.run(): %s", e)

try:
    from AI.collection_card.news_feed.main_news import run as newsfeed_run
except Exception as e:
    newsfeed_run = None
    logger.warning("Failed to import main_newsfeed.run(): %s", e)

# -----------------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------------
def health(request):
    return JsonResponse({"status": "ok", "version": "v1"})


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _parse_sources_param(val):
    if not val:
        return []
    if isinstance(val, list):
        raw = val
    elif isinstance(val, str):
        raw = [s.strip() for s in val.split(",") if s.strip()]
    else:
        raw = []
    seen = set()
    out = []
    for k in raw:
        if k in FETCHERS and k not in seen:
            seen.add(k)
            out.append(k)
    return out

# -----------------------------------------------------------------------------
# Built-in simple AI worker (fallback)
# -----------------------------------------------------------------------------
def _process_history_async(history_id: ObjectId, subject: str, batch_size: int = 50):
    db = get_mongo_db()
    mark_history_ai_started(history_id)
    try:
        if external_ai_run:
            rows = external_ai_run(str(history_id), subject)
        else:
            rows = None
        total = (
            len(rows)
            if rows is not None
            else db["ai_results"].count_documents(
                {"history_id": ObjectId(history_id), "status": "done"}
            )
        )
        mark_history_ai_done(history_id, total_count=total)
    except Exception as e:
        logger.exception("AI worker failed for history=%s: %s", history_id, e)


# -----------------------------------------------------------------------------
# External AI kicker (prefers AI.ranking_algorithm.main.run)
# -----------------------------------------------------------------------------
def _kick_external_ai(history_id: ObjectId, subject: str):
    db = get_mongo_db()
    try:
        mark_history_ai_started(history_id)

        if not external_ai_run:
            logger.warning("AI.main.run unavailable; using fallback worker.")
            _process_history_async(history_id, subject)
            return

        external_ai_run(str(history_id), subject)

        total = db["ai_results"].count_documents(
            {"history_id": ObjectId(history_id), "status": "done"}
        )
        mark_history_ai_progress(history_id, total)
        mark_history_ai_done(history_id, total_count=total)
        logger.info("External AI finished for history=%s, produced=%s items.", history_id, total)

    except Exception as e:
        logger.exception("External AI run failed; falling back. %s", e)
        _process_history_async(history_id, subject)


# -----------------------------------------------------------------------------
# Search + ingest
# -----------------------------------------------------------------------------
@api_view(["POST"])
def search_posts(request):
    """
    Pipeline (no preview in response):
      - Create a history record.
      - For each selected source, fetch (default 120).
      - Interleave, dedupe by URL, apply freshness window.
      - Persist up to persist_pool_limit into raw_insights (global cache).
      - Seed ai_results stubs (status='queued') for this history_id.
      - Kick external AI (or fallback worker) in a thread.
      - Return ONLY history_id + counts (no preview).
    """
    data = request.data or {}
    subject  = (data.get("subject")  or "").strip()
    location = (data.get("location") or "").strip()
    industry = (data.get("industry") or "").strip()

    if not subject:
        return Response({"error": "subject is required"}, status=status.HTTP_400_BAD_REQUEST)

    # # per-source fetch amount (increase pool)
    # try:
    #     fetch_limit = int(data.get("fetch_limit") or 120)
    # except Exception:
    #     fetch_limit = 120
    # fetch_limit = max(10, min(fetch_limit, 200))

    # # total to persist into raw_insights
    # try:
    #     persist_pool_limit = int(data.get("persist_pool_limit") or 500)
    # except Exception:
    #     persist_pool_limit = 500
    # persist_pool_limit = max(50, min(persist_pool_limit, 2000))

    # per-source fetch amount (reduce network/CPU)
    try:
        fetch_limit = int(data.get("fetch_limit") or 60)   # was 120
    except Exception:
        fetch_limit = 60
    fetch_limit = max(5, min(fetch_limit, 100))            # was 10..200

    # total to persist into raw_insights (reduce DB + AI load)
    try:
        persist_pool_limit = int(data.get("persist_pool_limit") or 300)  # was 500
    except Exception:
        persist_pool_limit = 300
    persist_pool_limit = max(50, min(persist_pool_limit, 800))           # was 50..2000

    # freshness window
    try:
        days = int(data.get("days") or 7)
    except Exception:
        days = 7

    # choose sources (default: all)
    selected = _parse_sources_param(data.get("sources") or data.get("source"))
    if not selected:
        selected = list(FETCHERS.keys())

    # Build upstream query
    query_terms = [subject]
    if location: query_terms.append(location)
    if industry: query_terms.append(industry)
    upstream_query = " ".join(query_terms)

    # Create history doc
    history_id = create_history(
        subject=subject,
        location=location,
        industry=industry,
        sources_used=selected,
        params={
            "days": days,
            "fetch_limit": fetch_limit,
            "persist_pool_limit": persist_pool_limit,
        },
        ai_target=100,
    )

    # Fetch per source
    sources_data = []
    per_source_counts = {}
    for key in selected:
        fn = FETCHERS[key]
        try:
            rows = fn(upstream_query, limit=fetch_limit)
        except Exception as e:
            logger.exception("%s error: %s", key, e)
            rows = []
        sources_data.append(rows)
        per_source_counts[key] = len(rows)

    # Interleave round-robin
    interleaved = []
    max_len = max((len(lst) for lst in sources_data), default=0)
    for i in range(max_len):
        for lst in sources_data:
            if i < len(lst):
                interleaved.append(lst[i])

    # Dedupe by URL
    seen = set()
    deduped = []
    for p in interleaved:
        u = (p.get("url") or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        deduped.append(p)

    # Freshness
    now = int(time.time())
    cutoff = now - days * 86400
    fresh = [p for p in deduped if (p.get("published_ts") or 0) >= cutoff] or deduped

    # Take first persist_pool_limit to save to raw_insights
    to_persist = fresh[:persist_pool_limit]
    created, updated = persist_raw_insights(to_persist)
    logger.info("raw_insights persisted: created=%d updated=%d (pool=%d)", created, updated, len(to_persist))

    # Seed per-run ai_results stubs so the AI knows what to process
    seeded = seed_ai_result_stubs(history_id, to_persist)

    # Prefer external AI if available; else fallback worker
    Thread(
        target=_kick_external_ai if external_ai_run else _process_history_async,
        args=(history_id, subject),
        daemon=True
    ).start()

    # Return ONLY the identifiers and counts (no preview)
    resp = Response({
        "history_id": str(history_id),
        "message": "Search queued. Poll /api/search/status and then fetch /api/results when ai_ready=true.",
        "counts": {
            "per_source": per_source_counts,
            "fetched_total": sum(per_source_counts.values()),
            "deduped": len(deduped),
            "fresh": len(fresh),
            "persisted": len(to_persist),
            "seeded_ai_results": seeded,
        }
    }, status=200)
    resp["X-Sources-Used"] = ",".join(selected)
    resp["X-Fetch-Limit"] = str(fetch_limit)
    resp["X-Persist-Pool-Limit"] = str(persist_pool_limit)
    resp["X-Freshness-Days"] = str(days)
    return resp


# -----------------------------------------------------------------------------
# NEW READ ENDPOINTS
# -----------------------------------------------------------------------------
@api_view(["GET"])
def list_history(request):
    try:
        db = get_mongo_db()
        limit = int(request.GET.get("limit", 20))
        limit = max(1, min(limit, 100))
        ai_ready_param = request.GET.get("ai_ready")
        filt = {}
        if ai_ready_param:
            filt["ai_ready"] = ai_ready_param.lower() == "true"

        docs = list(db["history"].find(filt).sort("created_at", -1).limit(limit))
        out = []
        for d in docs:
            out.append({
                "history_id": str(d["_id"]),
                "subject": d.get("subject"),
                "location": d.get("location"),
                "industry": d.get("industry"),
                "sources_used": d.get("sources_used", []),
                "created_at": d.get("created_at"),
                "ai_ready": d.get("ai_ready", False),
                "ai_count": d.get("ai_count", 0),
                "ai_target": d.get("ai_target", 100),
            })
        return Response(out, status=200)
    except Exception as e:
        logger.exception("list_history error: %s", e)
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
def get_search_status(request):
    hid = request.GET.get("history_id")
    if not hid:
        return Response({"error": "history_id is required"}, status=400)
    try:
        db = get_mongo_db()
        doc = db["history"].find_one({"_id": ObjectId(hid)})
        if not doc:
            return Response({"error": "not found"}, status=404)
        return Response({
            "history_id": str(doc["_id"]),
            "subject": doc.get("subject"),
            "ai_ready": doc.get("ai_ready", False),
            "ai_count": doc.get("ai_count", 0),
            "ai_target": doc.get("ai_target", 100),
            "created_at": doc.get("created_at"),
            "finished_at": doc.get("finished_at"),
        }, status=200)
    except Exception as e:
        logger.exception("get_search_status error: %s", e)
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
def get_trends(request):
    hid = request.GET.get("history_id")
    if not hid:
        return Response({"error": "history_id is required"}, status=400)
    try:
        days = int(request.GET.get("days", 30))
    except Exception:
        days = 30

    try:
        oid = ObjectId(hid)
        return Response({
            "history_id": hid,
            "window_days": days,
            "timeseries": trend_timeseries_by_day(oid, days),
            "top_tags": trend_top_tags(oid, days, top_k=20),
            "by_source": trend_by_source(oid, days),
        }, status=200)
    except Exception as e:
        logger.exception("get_trends error: %s", e)
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
def get_results(request):
    """
    GET /api/results?history_id=<id>&status=done&sort=rank&order=asc

    Returns ALL results for a history in a single array (no backend pagination).
    Frontend is responsible for slicing/pagination/display.

    Query params:
      - history_id (required) : ObjectId string for the run
      - status (optional)     : defaults to "done" (e.g., queued|processing|done)
      - sort   (optional)     : "rank" (default) | "published_ts" | "relevance_score"
      - order  (optional)     : "asc" (default) | "desc"
    """
    hid = (request.GET.get("history_id") or "").strip()
    if not hid:
        return Response({"error": "history_id is required"}, status=400)

    # filters
    status_filter = (request.GET.get("status") or "done").strip().lower()

    # sorting options
    sort_key = (request.GET.get("sort") or "rank").strip()
    order = (request.GET.get("order") or "asc").strip().lower()
    order_val = 1 if order in ("asc", "ascending") else -1

    # validate sort field
    valid_sort_fields = {"rank", "published_ts", "relevance_score"}
    if sort_key not in valid_sort_fields:
        sort_key = "rank"

    try:
        db = get_mongo_db()

        q = {"history_id": ObjectId(hid)}
        if status_filter:
            q["status"] = status_filter

        # Pull ALL matching docs; frontend handles pagination
        cursor = db["ai_results"].find(q).sort(sort_key, order_val)
        docs = list(cursor)

        results = []
        for d in docs:
            # Try to get engagement from either engagement_metrics or engagement field
            engagement = d.get("engagement_metrics") or d.get("engagement")

            results.append({
                "rank": d.get("rank"),
                "url": d.get("url"),
                "ai_title": d.get("ai_title"),
                "ai_summary": d.get("ai_summary"),
                "tags": d.get("tags"),
                "relevance_score": d.get("relevance_score"),
                "published_ts": d.get("published_ts"),
                "source": d.get("source"),
                "status": d.get("status"),
                "sentiment": d.get("sentiment"),
                "engagement_metrics": engagement,
                "engagement": engagement,  # Also include as 'engagement' for backward compatibility
            })

        return Response({
            "history_id": hid,
            "total": len(results),
            "results": results
        }, status=200)

    except Exception as e:
        logger.exception("get_results (no-pagination) error: %s", e)
        return Response({"error": str(e)}, status=500)


# -----------------------------------------------------------------------------
# Cards: Company-aware Trending Topics (primary endpoint for FE)
# -----------------------------------------------------------------------------
# ----------------------------------------------------------------------------- 
# Cards: Company-aware Trending Topics (schema is the source of truth)
# ----------------------------------------------------------------------------- 
# @api_view(["GET"])
# def card_trends(request):
#     """
#     GET /api/cards/trending/?company_id=<id>&threshold=0.5&limit=10&full=0
#       Optional:
#         - &company=<name> (resolve to id)
#         - &days=30 (window for global_top_topics)
#         - &full=1 (return [{"topic","relevance"}], else list[str])

#     Behavior:
#       - Source of truth: company_profiles.cards.trending.
#       - If today (UTC) < next_refresh_at.date() AND data exists -> return schema.
#       - Otherwise:
#           * build raw topics in-process via global_top_topics(days, pool>=limit)
#           * best-effort call trending_run(..., topics=raw_topics)
#           * MANUALLY persist schema with {data: list[str], updated_at, next_refresh_at=+7d}
#           * re-read schema and return (respecting full flag).
#     """
#     db = get_mongo_db()

#     # ----- inputs -----
#     company_id   = (request.GET.get("company_id") or "").strip() or None
#     company_name = (request.GET.get("company") or "").strip() or None

#     try:
#         threshold = float(request.GET.get("threshold", 0.5))
#     except Exception:
#         threshold = 0.5
#     try:
#         limit = int(request.GET.get("limit", 10))
#     except Exception:
#         limit = 10
#     limit = max(1, min(limit, 50))

#     full = (request.GET.get("full", "0").strip().lower() in ("1", "true"))
#     try:
#         days = int(request.GET.get("days", 30))
#     except Exception:
#         days = 30

#     # ----- resolve company -----
#     if not company_id and company_name:
#         doc = get_company_profile(name=company_name)
#         if not doc:
#             return Response({"error": f"Company '{company_name}' not found"}, status=404)
#         company_id = str(doc["_id"])
#     if not company_id:
#         return Response({"error": "company_id (or company name) is required"}, status=400)

#     # ----- helper: read schema + respond -----
#     def _read_from_db_and_respond():
#         fresh = db["company_profiles"].find_one(
#             {"_id": ObjectId(company_id)},
#             {"cards.trending": 1}
#         )
#         if not fresh:
#             return Response({"error": "company profile not found"}, status=404)

#         trending = ((fresh.get("cards") or {}).get("trending") or {})
#         data = trending.get("data") or []

#         # shape control
#         if full:
#             # if stored strings → wrap with null relevance
#             if data and isinstance(data[0], str):
#                 wrapped = [{"topic": t, "relevance": None} for t in data]
#                 return Response(wrapped[:limit], status=200)
#             # already dicts
#             return Response((data or [])[:limit], status=200)
#         else:
#             if data and isinstance(data[0], dict):
#                 topics = [x.get("topic") for x in data if isinstance(x, dict) and x.get("topic")]
#                 return Response(topics[:limit], status=200)
#             return Response((data or [])[:limit], status=200)

#     # ----- freshness check -----
#     prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards.trending": 1})
#     trending = ((prof or {}).get("cards") or {}).get("trending") or {}
#     next_refresh_at = trending.get("next_refresh_at")
#     next_refresh_date = _parse_iso_to_date(next_refresh_at)
#     today_utc = datetime.now(timezone.utc).date()

#     if next_refresh_date and today_utc < next_refresh_date and (trending.get("data") or []):
#         return _read_from_db_and_respond()

#     # ----- build raw topics locally (no HTTP) -----
#     # ask for a bigger pool than limit so the runner has room
#     pool = max(30, limit)
#     try:
#         raw_topics = global_top_topics(days=max(days, 30), limit=pool)  # -> list[str]
#     except Exception as e:
#         logger.exception("global_top_topics failed: %s", e)
#         # even if generation failed, return whatever is in schema
#         return _read_from_db_and_respond()

#     # ----- best-effort: call AI runner with raw topics -----
#     # If AI supports a topics list, we pass it. If not, this will no-op harmlessly.
#     if trending_run is not None:
#         try:
#             # prefer named arg 'topics' (common), fall back to 'topics_list' if needed.
#             try:
#                 trending_run(
#                     company_id=company_id,
#                     topics=raw_topics,              # <--- pass raw list here
#                     threshold=threshold,
#                     full_analysis=full,
#                     verbose=False,
#                     limit=limit,
#                 )
#             except TypeError:
#                 # alt signature
#                 trending_run(
#                     company_id=company_id,
#                     topics_list=raw_topics,         # <--- alternate name
#                     threshold=threshold,
#                     full_analysis=full,
#                     verbose=False,
#                     limit=limit,
#                 )
#         except Exception as e:
#             logger.warning("trending_run failed; proceeding with manual persist. %s", e)

#     # ----- manual persist to schema (list[str]) -----
#     try:
#         now = datetime.now(timezone.utc)
#         new_block = {
#             "data": (raw_topics or [])[:limit],       # store list[str] in schema
#             "updated_at": _iso_z(now),
#             "next_refresh_at": _iso_z(now + timedelta(days=7)),
#         }
#         db["company_profiles"].update_one(
#             {"_id": ObjectId(company_id)},
#             {"$set": {"cards.trending": new_block}}
#         )
#     except Exception as e:
#         logger.exception("Manual trending persist failed: %s", e)
#         # fall back to whatever is currently stored
#         return _read_from_db_and_respond()

#     # ----- re-read schema and return -----
#     return _read_from_db_and_respond()

# @api_view(["GET"]) #original
# def card_trends(request):
#     """
#     GET /api/cards/trending/?company_id=<id>&threshold=0.5&limit=10&full=0
#       Optional:
#         - &company=<name> (resolve to id)
#         - &days=30 (window for global_top_topics)
#         - &full=1 (return [{"topic","relevance"}], else list[str])

#     Source of truth: company_profiles.cards.trending
#     - If today (UTC) < next_refresh_at.date() and data exists -> return schema
#     - Else:
#         * build raw_topics via global_top_topics(days, pool>=limit)
#         * call trending_run(company_id, trending_topics=raw_topics)
#         * re-read schema and return
#         * (compat) if AI wrote to 'trending_topics', migrate to 'trending'
#         * (safety) if next_refresh_at missing, set to now+7d
#     """
#     db = get_mongo_db()

#     # ----- inputs -----
#     company_id   = (request.GET.get("company_id") or "").strip() or None
#     company_name = (request.GET.get("company") or "").strip() or None
#     force = str(request.GET.get("force", "0")).strip().lower() in ("1", "true", "yes", "y", "on")


#     try:
#         threshold = float(request.GET.get("threshold", 0.5))
#     except Exception:
#         threshold = 0.5
#     try:
#         limit = int(request.GET.get("limit", 10))
#     except Exception:
#         limit = 10
#     limit = max(1, min(limit, 50))

#     full = (request.GET.get("full", "0").strip().lower() in ("1", "true"))
#     try:
#         days = int(request.GET.get("days", 30))
#     except Exception:
#         days = 30

#     # ----- resolve company -----
#     if not company_id and company_name:
#         doc = get_company_profile(name=company_name)
#         if not doc:
#             return Response({"error": f"Company '{company_name}' not found"}, status=404)
#         company_id = str(doc["_id"])
#     if not company_id:
#         return Response({"error": "company_id (or company name) is required"}, status=400)

#     # ----- helper: read schema + respond -----
#     def _read_from_db_and_respond():
#         fresh = db["company_profiles"].find_one(
#             {"_id": ObjectId(company_id)},
#             {"cards.trending": 1}
#         )
#         if not fresh:
#             return Response({"error": "company profile not found"}, status=404)

#         trending = ((fresh.get("cards") or {}).get("trending") or {})
#         data = trending.get("data") or []

#         if full:
#             if data and isinstance(data[0], str):
#                 return Response([{"topic": t, "relevance": None} for t in data][:limit], status=200)
#             return Response((data or [])[:limit], status=200)
#         else:
#             if data and isinstance(data[0], dict):
#                 topics = [x.get("topic") for x in data if isinstance(x, dict) and x.get("topic")]
#                 return Response(topics[:limit], status=200)
#             return Response((data or [])[:limit], status=200)

#     # ----- freshness check -----
#     prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards": 1})
#     cards = (prof or {}).get("cards") or {}
#     trending = cards.get("trending") or {}
#     next_refresh_at = trending.get("next_refresh_at")
#     next_refresh_date = _parse_iso_to_date(next_refresh_at)
#     today_utc = datetime.now(timezone.utc).date()

#     # Only short-circuit if NOT forcing
#     if not force and next_refresh_date and today_utc < next_refresh_date and (trending.get("data") or []):
#         return _read_from_db_and_respond()


#     # ----- build raw topics locally -----
#     pool = max(30, limit)
#     try:
#         raw_topics = global_top_topics(days=max(days, 30), limit=pool)  # list[str]
#     except Exception as e:
#         logger.exception("global_top_topics failed: %s", e)
#         return _read_from_db_and_respond()

#     # ----- call AI runner (now authoritative persister) -----
#     if trending_run is not None:
#         try:
#             trending_run(
#                 company_id=company_id,
#                 trending_topics=raw_topics,   # <-- new param name
#                 # runner may ignore the below, but keep for future compatibility
#                 # threshold=threshold, full_analysis=full, limit=limit
#             )
#         except Exception as e:
#             logger.warning("trending_run failed; returning schema as-is. %s", e)
#             return _read_from_db_and_respond()

#     # ----- compatibility + safety: migrate & ensure next_refresh_at -----
#     # Re-read full cards so we can migrate if needed
#     fresh = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards": 1}) or {}
#     cards = fresh.get("cards") or {}

#     # If AI wrote to 'trending_topics', copy to 'trending'
#     if "trending_topics" in cards and (not cards.get("trending") or not (cards["trending"].get("data") or [])):
#         src = cards["trending_topics"] or {}
#         block = {
#             "data": src.get("data") or [],
#             "updated_at": src.get("updated_at") or _iso_z(datetime.now(timezone.utc)),
#             "next_refresh_at": src.get("next_refresh_at") or None,
#         }
#         db["company_profiles"].update_one(
#             {"_id": ObjectId(company_id)},
#             {"$set": {"cards.trending": block}}
#         )
#         # refresh view data
#         fresh = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards.trending": 1}) or {}

#     # Ensure next_refresh_at exists (runner example set it to None)
#     cur = ((fresh.get("cards") or {}).get("trending") or {})
#     if not cur.get("next_refresh_at"):
#         now = datetime.now(timezone.utc)
#         db["company_profiles"].update_one(
#             {"_id": ObjectId(company_id)},
#             {"$set": {"cards.trending.next_refresh_at": _iso_z(now + timedelta(days=7))}}
#         )

#     # ----- final: re-read and return schema -----
#     return _read_from_db_and_respond()


# @api_view(["GET"])
# def card_trends(request):
#     """
#     GET /api/cards/trending/?company_id=<id>&threshold=0.5&limit=10&full=0
#     Optional:
#       - &company=<name> (if you don't have company_id; we resolve it to an ID)
#       - &api_url=<endpoint that returns topics or {"topics":[...]}>

#     Returns:
#       - full=0 (default): ["topic A", "topic B", ...]
#       - full=1: [{"topic": "...", "relevance": 0.87}, ...]
#     """
#     if trending_run is None:
#         return Response({"error": "trending.run not available"}, status=500)

#     company_id   = (request.GET.get("company_id") or "").strip() or None
#     company_name = (request.GET.get("company") or "").strip() or None
#     api_url      = (request.GET.get("api_url") or "").strip() or None

#     try:
#         threshold = float(request.GET.get("threshold", 0.5))
#     except Exception:
#         threshold = 0.5

#     try:
#         limit = int(request.GET.get("limit", 10))
#     except Exception:
#         limit = 10
#     limit = max(1, min(limit, 50))

#     full = (request.GET.get("full", "0").strip().lower() in ("1", "true"))

#     try:
#         # Resolve company_id by name if needed
#         if not company_id and company_name:
#             doc = get_company_profile(name=company_name)
#             if not doc:
#                 return Response({"error": f"Company '{company_name}' not found"}, status=404)
#             company_id = str(doc["_id"])

#         if not company_id:
#             return Response({"error": "company_id (or company name) is required"}, status=400)

#         # Default API for topics if not provided (ask for a bigger pool than limit)
#         if not api_url:
#             api_url = f"http://127.0.0.1:8001/api/topics/top/?days=30&limit={max(30, limit)}"

#         # 🔥 Call your AI module's main run()
#         results = trending_run(
#             company_id=company_id,
#             api_url=api_url,
#             threshold=threshold,
#             full_analysis=full,
#             verbose=False,
#             limit=limit,  # your run() already trims to limit
#         )

#         # Just in case the runner didn't trim:
#         if isinstance(results, list):
#             results = results[:limit]

#         return Response(results, status=200)

#     except Exception as e:
#         logger.exception("card_trends error: %s", e)
#         return Response({"error": str(e)}, status=500)

    
# @api_view(["GET"])
# def card_trends(request):
#     result = get_news_articles("http://127.0.0.1:8001/api/topics/top/?days=30&limit=10", verbose=True)

#     return result
    # """
    # GET /api/cards/trending/?company_id=<id>&threshold=0.5&limit=10
    # Optional: &company=<name> (fallback if id not supplied)
    # Returns: [{ "topic": str, "relevance": float }, ...]
    # """
    # if analyse_relevancy is None:
    #     return Response({"error": "AI relevancy module not available"}, status=500)

    # company_name = (request.GET.get("company") or "").strip() or None
    # company_id = (request.GET.get("company_id") or "").strip() or None

    # try:
    #     threshold = float(request.GET.get("threshold", 0.5))
    # except Exception:
    #     threshold = 0.5
    # try:
    #     limit = int(request.GET.get("limit", 10))
    # except Exception:
    #     limit = 10
    # limit = max(1, min(limit, 50))

    # try:
    #     # 1) Company context from Mongo
    #     cname, description, competitors = _build_company_context(company_name, company_id)
    #     context = {
    #         "company": cname,
    #         "description": description,
    #         "competitors": competitors,
    #         "recent_searches": [],  # can enrich later if needed
    #     }

    #     # 2) Build trending topics internally (no HTTP dependency)
    #     topics = global_top_topics(days=30, limit=30)

    #     # 3) AI relevance scoring
    #     analysis_raw = analyse_relevancy.relevancy_rag(context, topics)
    #     analysis_list = _coerce_ai_list(analysis_raw)

    #     # 4) Filter + limit
    #     filtered = [
    #         x for x in analysis_list
    #         if float(x.get("relevance", 0)) >= threshold
    #     ][:limit]

    #     return Response(filtered, status=200)

    # except ValueError as e:
    #     # AI returned a plain error string or malformed JSON
    #     logger.warning("card_trends validation/AI error: %s", e)
    #     return Response({"error": str(e)}, status=502)
    # except Exception as e:
    #     logger.exception("card_trends error: %s", e)
    #     return Response({"error": str(e)}, status=500)

@api_view(["GET"])
def card_trends(request):
    """
    GET /api/cards/trending/?company_id=<id>&threshold=0.5&limit=10&full=0&force=0
      Optional:
        - &company=<name> (resolve to id)
        - &days=30        (time window hint for Trends)
        - &geo=AU         (Google Trends region, e.g., AU, US)
        - &use_serpapi=1  (toggle external fetch; if 0, falls back to global_top_topics)
        - &query=<str>    (override query for related topics; defaults to company name)
        - &full=1         (return [{"topic","relevance"}], else list[str])

    Source of truth: company_profiles.cards.trending
    - If not force AND today(UTC) < next_refresh_at.date() AND data exists -> return schema.
    - Else:
        * Build raw_topics via SerpAPI Google Trends (or fallback global_top_topics).
        * Call trending_run(company_id, trending_topics=raw_topics).
        * Re-read schema and return.
        * (compat) if AI wrote to 'trending_topics', migrate -> 'trending'.
        * (safety) ensure next_refresh_at exists (now + 7d).
    """
    db = get_mongo_db()

    # ----- inputs -----
    company_id   = (request.GET.get("company_id") or "").strip() or None
    company_name = (request.GET.get("company") or "").strip() or None
    force        = str(request.GET.get("force", "0")).strip().lower() in ("1", "true", "yes", "y", "on")
    use_serpapi  = str(request.GET.get("use_serpapi", "1")).strip().lower() in ("1", "true", "yes", "y", "on")
    geo          = (request.GET.get("geo") or "AU").strip().upper()
    override_q   = (request.GET.get("query") or "").strip() or None

    try:
        threshold = float(request.GET.get("threshold", 0.5))
    except Exception:
        threshold = 0.5
    try:
        limit = int(request.GET.get("limit", 10))
    except Exception:
        limit = 10
    limit = max(1, min(limit, 50))

    full = (request.GET.get("full", "0").strip().lower() in ("1", "true"))
    try:
        days = int(request.GET.get("days", 30))
    except Exception:
        days = 30

    # ----- resolve company -----
    if not company_id and company_name:
        doc = get_company_profile(name=company_name)
        if not doc:
            return Response({"error": f"Company '{company_name}' not found"}, status=404)
        company_id = str(doc["_id"])
    if not company_id:
        return Response({"error": "company_id (or company name) is required"}, status=400)

    # ----- helper: read schema + respond -----
    def _read_from_db_and_respond():
        fresh = db["company_profiles"].find_one(
            {"_id": ObjectId(company_id)},
            {"cards.trending": 1}
        ) or {}
        trending = ((fresh.get("cards") or {}).get("trending") or {})
        data = trending.get("data") or []

        if full:
            if data and isinstance(data[0], str):
                return Response([{"topic": t, "relevance": None} for t in data][:limit], status=200)
            return Response((data or [])[:limit], status=200)
        else:
            if data and isinstance(data[0], dict):
                topics = [x.get("topic") for x in data if isinstance(x, dict) and x.get("topic")]
                return Response(topics[:limit], status=200)
            return Response((data or [])[:limit], status=200)

    # ----- freshness check -----
    prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards": 1}) or {}
    cards = prof.get("cards") or {}
    trending = cards.get("trending") or {}
    next_refresh_at   = trending.get("next_refresh_at")
    next_refresh_date = _parse_iso_to_date(next_refresh_at)
    today_utc         = datetime.now(timezone.utc).date()

    if not force and next_refresh_date and today_utc < next_refresh_date and (trending.get("data") or []):
        return _read_from_db_and_respond()

        # ----- build raw topics (SerpAPI first; fallback to global_top_topics) -----
    raw_topics: list[str] = []
    if use_serpapi:
        q_for_trends = override_q or company_name or None
        try:
            pool = max(30, limit)
            raw_topics = _fetch_trending_topics_serpapi(
                q_for_trends,
                geo=geo or "AU",
                days=max(days, 30),
                limit=pool,
                api_key=SERPAPI_DEFAULT_KEY,
            )
        except Exception as e:
            logger.warning("SerpAPI (Google Trends) fetch failed; falling back. %s", e)

    if not raw_topics:
        try:
            raw_topics = global_top_topics(days=max(days, 30), limit=max(30, limit))
        except Exception as e:
            logger.exception("global_top_topics failed: %s", e)
            return _read_from_db_and_respond()

    # >>> NEW: sanitize aggressively <<<
    raw_topics = _sanitize_topics(raw_topics, max_len=60)
    if not raw_topics:
        # Nothing clean → just return whatever’s there
        
        return _read_from_db_and_respond()

    # ----- call AI runner (authoritative persister) -----
    runner_ok = True
    if trending_run is not None:
        try:
            trending_run(
                company_id=company_id,
                trending_topics=raw_topics,
            )
        except Exception as e:
            runner_ok = False
            logger.warning("trending_run failed; will fallback-persist sanitized topics. %s", e)
    else:
        runner_ok = False

    # ----- compatibility + safety -----
    fresh = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards": 1}) or {}
    cards = fresh.get("cards") or {}

    if "trending_topics" in cards and (not cards.get("trending") or not (cards["trending"].get("data") or [])):
        src = cards["trending_topics"] or {}
        block = {
            "data": src.get("data") or [],
            "updated_at": src.get("updated_at") or _iso_z(datetime.now(timezone.utc)),
            "next_refresh_at": src.get("next_refresh_at") or None,
        }
        db["company_profiles"].update_one(
            {"_id": ObjectId(company_id)},
            {"$set": {"cards.trending": block}}
        )
        fresh = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards.trending": 1}) or {}

    # >>> NEW: if runner failed and nothing got written, persist sanitized topics as strings <<<
    cur = ((fresh.get("cards") or {}).get("trending") or {})
# NEW: if runner failed AND (force OR no existing data) -> overwrite
    if (not runner_ok) and (force or not (cur.get("data") or [])):

        now = datetime.now(timezone.utc)
        block = {
            "data": raw_topics[:limit],                     # store as list[str]
            "updated_at": _iso_z(now),
            "next_refresh_at": _iso_z(now + timedelta(days=7)),
        }
        db["company_profiles"].update_one(
            {"_id": ObjectId(company_id)},
            {"$set": {"cards.trending": block}}
        )
        # refresh 'cur' for the next step
        cur = block

    # Ensure next_refresh_at exists
    if not cur.get("next_refresh_at"):
        now = datetime.now(timezone.utc)
        db["company_profiles"].update_one(
            {"_id": ObjectId(company_id)},
            {"$set": {"cards.trending.next_refresh_at": _iso_z(now + timedelta(days=7))}}
        )

    # ----- final: re-read and return schema -----
    return _read_from_db_and_respond()

# -----------------------------------------------------------------------------
# Cards: Company-aware News (optional, for parity/testing)
# -----------------------------------------------------------------------------

@api_view(["GET"])
def news_feed(request):
    """
    GET /api/cards/newsfeed/?company_id=<id>&limit=10&max_age_days=7&force=0
      Optional:
        - &company=<name>        (resolve to id)
        - &sources=bbc_rss,techcrunch_rss,news_rss   (allowlist when reading raw_insights)
        - &use_newsapi=1         (also pull from NewsAPI if pool is small)
        - &query=<string>        (NewsAPI query fallback; defaults to company name)
        - &page_size=50          (NewsAPI page size; 10..100)

    Source of truth: company_profiles.cards.newsfeed
    - If not force AND today(UTC) < next_refresh_at.date() AND data exists -> return schema.
    - Else:
        * Build raw_articles from raw_insights (within max_age_days, allowed sources).
        * Optionally augment with NewsAPI (when use_newsapi=1).
        * Call newsfeed_run(company_id, news_articles=raw_articles).
        * Re-read schema and return.
        * (compat) if AI wrote to 'news_feed', migrate to 'newsfeed'.
        * (safety) if next_refresh_at missing, set to now+7d.
    """
    db = get_mongo_db()

    # ----- inputs -----
    company_id   = (request.GET.get("company_id") or "").strip() or None
    company_name = (request.GET.get("company") or "").strip() or None
    force        = str(request.GET.get("force", "0")).strip().lower() in ("1", "true", "yes", "y", "on")

    try:
        limit = int(request.GET.get("limit", 10))
    except Exception:
        limit = 10
    limit = max(1, min(limit, 100))

    try:
        max_age_days = int(request.GET.get("max_age_days", 7))
    except Exception:
        max_age_days = 7

    # Sources allowlist (when reading raw_insights)
    sources_param = (request.GET.get("sources") or "").strip()
    if sources_param:
        allowed_sources = {s.strip() for s in sources_param.split(",") if s.strip()}
    else:
        allowed_sources = {
            "news_rss", "bbc_rss", "techcrunch_rss", "guardian_api", "google_news_rss",
            "abc_au_rss", "cnn_rss", "reuters_rss"
        }

    # Optional external enrichment
    use_newsapi = str(request.GET.get("use_newsapi", "0")).strip().lower() in ("1", "true", "yes", "y", "on")
    query       = (request.GET.get("query") or "").strip()
    try:
        page_size = int(request.GET.get("page_size", 50))
    except Exception:
        page_size = 50

    # ----- resolve company -----
    if not company_id and company_name:
        doc = get_company_profile(name=company_name)
        if not doc:
            return Response({"error": f"Company '{company_name}' not found"}, status=404)
        company_id = str(doc["_id"])
    if company_id and not company_name:
        prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"name": 1})
        if prof:
            company_name = prof.get("name")
    if not company_id:
        # fallback: latest profile
        doc = get_company_profile(name=None)
        if not doc:
            return Response({"error": "company_id (or company name) is required"}, status=400)
        company_id = str(doc["_id"])
        company_name = company_name or doc.get("name")

    # ----- helper: read schema + respond -----
    def _read_from_db_and_respond():
        fresh = db["company_profiles"].find_one(
            {"_id": ObjectId(company_id)},
            {"name": 1, "cards.newsfeed": 1}
        ) or {}
        name  = fresh.get("name") or company_name
        card  = ((fresh.get("cards") or {}).get("newsfeed") or {})
        data  = (card.get("data") or [])[:limit]
        return Response({"company": name, "company_id": company_id, "count": len(data), "items": data}, status=200)

    # ----- freshness check -----
    prof  = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards": 1}) or {}
    cards = prof.get("cards") or {}
    nf    = cards.get("newsfeed") or {}
    next_refresh_at   = nf.get("next_refresh_at")
    next_refresh_date = _parse_iso_to_date(next_refresh_at)
    today_utc         = datetime.now(timezone.utc).date()

    if not force and next_refresh_date and today_utc < next_refresh_date and (nf.get("data") or []):
        return _read_from_db_and_respond()

    # ----- build local raw article pool from raw_insights -----
    now_ts   = int(time.time())
    cutoff   = now_ts - max_age_days * 86400
    pool_cap = 100
    # pool_min = max(3 * limit, 2)  # aim for enough for AI to filter
    pool_min = 50

    def _ts_to_iso_z(ts: int | None):
        if not ts:
            return None
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat().replace("+00:00", "Z")
        except Exception:
            return None

    cursor = (
        db["raw_insights"]
        .find(
            {"published_ts": {"$gte": cutoff}, "source": {"$in": list(allowed_sources)}},
            {"title": 1, "url": 1, "source": 1, "published_ts": 1, "text": 1, "author": 1, "summary": 1}
        )
        .sort("published_ts", -1)
        .limit(pool_cap)
    )

    raw_articles = []
    for r in cursor:
        title = (r.get("title") or "").strip()
        url   = (r.get("url") or "").strip()
        if not title or not url:
            continue
        raw_articles.append({
            "title": title,
            "description": (r.get("summary") or r.get("text") or "").strip(),
            "url": url,
            "author": (r.get("author") or None),
            "source": r.get("source"),
            "publishedAt": _ts_to_iso_z(r.get("published_ts")),
        })

    # ----- optionally augment via NewsAPI if pool seems small -----
    if use_newsapi:
        q = query or company_name or ""
        try:
            extra = _fetch_from_newsapi(q, api_key=NEWSAPI_DEFAULT_KEY, page_size=page_size)
        except Exception as e:
            logger.warning("NewsAPI fetch failed: %s", e)
            extra = []

        # de-dup by URL
        seen = {a["url"] for a in raw_articles if a.get("url")}
        for a in (extra or []):
            u = (a.get("url") or "").strip()
            if u and u not in seen:
                raw_articles.append(a)
                seen.add(u)

    # trim to desired pool size for AI
    raw_articles = raw_articles[:max(pool_min, limit)]

    # If absolutely nothing, return empty schema-like response
    if not raw_articles:
        # also ensure there is a next_refresh_at so FE won’t hammer
        now = datetime.now(timezone.utc)
        db["company_profiles"].update_one(
            {"_id": ObjectId(company_id)},
            {"$set": {"cards.newsfeed.next_refresh_at": _iso_z(now + timedelta(days=1))}},
            upsert=True,
        )
        return Response({"company": company_name, "company_id": company_id, "count": 0, "items": []}, status=200)

    # ----- call AI runner (authoritative persister) -----
    if newsfeed_run is not None:
        try:
            newsfeed_run(company_id=company_id, news_articles=raw_articles)
        except Exception as e:
            logger.warning("newsfeed_run failed; continuing with schema migration/safety. %s", e)

    # ----- compatibility + safety: migrate & ensure next_refresh_at -----
    fresh = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards": 1}) or {}
    cards = fresh.get("cards") or {}

    # If AI wrote to 'news_feed', copy to 'newsfeed' (your schema-of-truth)
    if "news_feed" in cards and (not cards.get("newsfeed") or not (cards["newsfeed"].get("data") or [])):
        src = cards["news_feed"] or {}
        block = {
            "data": src.get("data") or [],
            "updated_at": src.get("updated_at") or _iso_z(datetime.now(timezone.utc)),
            "next_refresh_at": src.get("next_refresh_at") or None,
        }
        db["company_profiles"].update_one(
            {"_id": ObjectId(company_id)},
            {"$set": {"cards.newsfeed": block}}
        )
        fresh = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards.newsfeed": 1}) or {}

    # Ensure next_refresh_at exists
    cur = ((fresh.get("cards") or {}).get("newsfeed") or {})
    if not cur.get("next_refresh_at"):
        now = datetime.now(timezone.utc)
        db["company_profiles"].update_one(
            {"_id": ObjectId(company_id)},
            {"$set": {"cards.newsfeed.next_refresh_at": _iso_z(now + timedelta(days=7))}}
        )


        # ----- final: re-read schema -----
    return _read_from_db_and_respond()


# -----------------------------------------------------------------------------
# Debug
# -----------------------------------------------------------------------------
@api_view(["GET"])
def mongo_status(request):
    try:
        db = get_mongo_db()
        names = sorted(db.list_collection_names())
        counts = {}
        for c in ["raw_insights", "ai_results", "history"]:
            if c in names:
                counts[c] = db[c].count_documents({})
        return Response({"db": db.name, "collections": names, "counts": counts}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
def get_top_topics(request):
    """
    GET /api/topics/top?days=30&limit=15
    Returns a simple list of trending topic tags.
    """
    days = int(request.GET.get("days", 30))
    limit = int(request.GET.get("limit", 15))
    try:
        data = global_top_topics(days=days, limit=limit)
        return Response({"window_days": days, "topics": data}, status=200)
    except Exception as e:
        logger.exception("get_top_topics error: %s", e)
        return Response({"error": str(e)}, status=500)

# @api_view(["GET"])
# def ai_generate_ideas(request):
#     """
#     GET /api/ai/ideas/?company=EcoDrive%20Motors&type=all&limit=10

#     Behavior (same as card_trends):
#       - Always return what's stored in company_profiles.cards.ideas.
#       - If today (UTC) >= next_refresh_at.date() OR next_refresh_at missing:
#           * try ideas_run(...) (best-effort; may persist itself)
#           * persist manually if ideas_run returns a list
#           * re-read doc from Mongo and return that.
#     """
#     db = get_mongo_db()

#     # inputs
#     company_id   = (request.GET.get("company_id") or "").strip() or None
#     company_name = (request.GET.get("company") or "").strip() or None
#     insight_type = (request.GET.get("type") or "all").lower()
#     try:
#         limit = int(request.GET.get("limit", 10))
#     except Exception:
#         limit = 10
#     limit = max(1, min(limit, 100))

#     # resolve company
#     if not company_id and not company_name:
#         return Response({"error": "company_id (or company name) is required"}, status=400)
#     if not company_id and company_name:
#         doc = get_company_profile(name=company_name)
#         if not doc:
#             return Response({"error": f"Company '{company_name}' not found"}, status=404)
#         company_id = str(doc["_id"])
#     if company_id and not company_name:
#         prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"name": 1})
#         if prof:
#             company_name = prof.get("name")

#     # helper: read schema + respond
#     def _read_schema_and_respond():
#         fresh = db["company_profiles"].find_one(
#             {"_id": ObjectId(company_id)},
#             {"name": 1, "cards.ideas": 1}
#         )
#         if not fresh:
#             return Response({"error": "company profile not found"}, status=404)
#         name = fresh.get("name") or company_name
#         ideas_card = ((fresh.get("cards") or {}).get("ideas") or {})
#         data = (ideas_card.get("data") or [])[:limit]
#         return Response(
#             {"company": name, "company_id": company_id, "count": len(data), "insights": data},
#             status=200,
#         )

#     # freshness check (same logic as trending)
#     prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards.ideas": 1})
#     ideas_card = ((prof or {}).get("cards") or {}).get("ideas") or {}
#     next_refresh_at = ideas_card.get("next_refresh_at")
#     next_refresh_date = _parse_iso_to_date(next_refresh_at)
#     today_utc = datetime.now(timezone.utc).date()

#     if next_refresh_date and today_utc < next_refresh_date and (ideas_card.get("data") or []):
#         return _read_schema_and_respond()

#     # refresh path
#     if ideas_run is None:
#         # no runner → fall back to whatever is stored
#         return _read_schema_and_respond()

#     try:
#         insights = ideas_run(
#             company_id=company_id,
#             company_name=company_name,
#             insight_type=insight_type,
#             limit=limit,
#             verbose=False,
#         )

#         # If runner returned data but didn't persist, we persist here.
#         if isinstance(insights, list):
#             now = datetime.now(timezone.utc)
#             new_block = {
#                 "data": insights[:limit],                 # list[dict] from ideas_run
#                 "updated_at": _iso_z(now),
#                 "next_refresh_at": _iso_z(now + timedelta(days=7)),  # same +7d rule
#             }
#             db["company_profiles"].update_one(
#                 {"_id": ObjectId(company_id)},
#                 {"$set": {"cards.ideas": new_block}}
#             )
#     except Exception as e:
#         logger.warning("ideas_run failed; returning schema as-is. %s", e)

#     # re-read and return schema value
#     return _read_schema_and_respond()

@api_view(["GET"])
def ai_generate_ideas(request):
    """
    GET /api/ai/ideas/?company_id=<id>&limit=10&force=0
      Optional:
        - &company=<name> (resolve to id if you prefer names)
        - &limit=10 (response trim only)
        - &force=1 (ignore freshness and recompute)

    Source of truth: company_profiles.cards.ideas
    - If today (UTC) < next_refresh_at.date() and data exists -> return schema
    - Else:
        * call ideas_run(company_id=...)
        * re-read schema and return
        * (safety) if next_refresh_at missing, set to now+7d
    """
    db = get_mongo_db()

    # ----- inputs -----
    company_id   = (request.GET.get("company_id") or "").strip() or None
    company_name = (request.GET.get("company") or "").strip() or None
    force        = str(request.GET.get("force", "0")).strip().lower() in ("1", "true", "yes", "y", "on")

    try:
        limit = int(request.GET.get("limit", 10))
    except Exception:
        limit = 10
    limit = max(1, min(limit, 100))

    # ----- resolve company -----
    if not company_id and company_name:
        doc = get_company_profile(name=company_name)
        if not doc:
            return Response({"error": f"Company '{company_name}' not found"}, status=404)
        company_id = str(doc["_id"])

    if not company_id:
        return Response({"error": "company_id (or company name) is required"}, status=400)

    # ----- helper: read schema + respond -----
    def _read_schema_and_respond():
        fresh = db["company_profiles"].find_one(
            {"_id": ObjectId(company_id)},
            {"name": 1, "cards.ideas": 1}
        ) or {}
        name = fresh.get("name") or company_name

        ideas_card = ((fresh.get("cards") or {}).get("ideas") or {})

        # --- compatibility: accept legacy keys ---
        data = ideas_card.get("data")
        if not data:
            # legacy shapes we’ve seen in runner code
            data = ideas_card.get("ideas") or ideas_card.get("items") or []

            # optional: migrate to normalized key so next read is clean
            if data:
                db["company_profiles"].update_one(
                    {"_id": ObjectId(company_id)},
                    {"$set": {"cards.ideas.data": data}},
                )
                ideas_card["data"] = data  # keep local var in sync

        data = (data or [])[:limit]

        return Response(
            {"company": name, "company_id": company_id, "count": len(data), "insights": data},
            status=200,
        )


    # ----- freshness check (skip if force) -----
    prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards": 1})
    cards = (prof or {}).get("cards") or {}
    ideas_card = cards.get("ideas") or {}
    next_refresh_at = ideas_card.get("next_refresh_at")
    next_refresh_date = _parse_iso_to_date(next_refresh_at)
    today_utc = datetime.now(timezone.utc).date()

    if not force and next_refresh_date and today_utc < next_refresh_date and (ideas_card.get("data") or []):
        return _read_schema_and_respond()

    # ----- call AI runner (authoritative persister) -----
    # Only pass company_id, per your requirement.
    if ideas_run is not None:
        try:
            ideas_run(company_id=company_id)
        except Exception as e:
            logger.warning("ideas_run failed; returning schema as-is. %s", e)
            return _read_schema_and_respond()

    # ----- safety: ensure next_refresh_at exists (+7d) -----
    fresh = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards.ideas": 1}) or {}
    cur = ((fresh.get("cards") or {}).get("ideas") or {})
    if not cur.get("next_refresh_at"):
        now = datetime.now(timezone.utc)
        db["company_profiles"].update_one(
            {"_id": ObjectId(company_id)},
            {"$set": {"cards.ideas.next_refresh_at": _iso_z(now + timedelta(days=7))}}
        )

    # ----- final: re-read and return -----
    return _read_schema_and_respond()


@api_view(["GET", "POST"])
def ai_competitors(request):
    """
    GET  /api/ai/competitors/?company_id=<id>
    POST /api/ai/competitors/
         { "company_id": "<id>" }

    Returns:
      [ "Tesla Motors", "BYD Auto", "Rivian Automotive" ]
    """
    try:
        db = get_mongo_db()

        # Accept both GET or POST input
        data = request.data if request.method == "POST" else request.GET
        company_id = (data.get("company_id") or "").strip()

        if not company_id:
            return Response({"error": "company_id is required"}, status=400)

        # Validate ObjectId format
        try:
            oid = ObjectId(company_id)
        except Exception:
            return Response({"error": "invalid company_id (must be 24-character ObjectId)"}, status=400)

        # Find company document
        doc = db["company_profiles"].find_one({"_id": oid})
        if not doc:
            return Response({"error": "company not found"}, status=404)

        # Return competitors field
        competitors = doc.get("competitors", [])
        return Response(competitors, status=200)

    except Exception as e:
        logger.exception("ai_competitors error: %s", e)
        return Response({"error": str(e)}, status=500)



# Accept GET to match your cards pattern (keeps POST body fallback for compatibility)
# @api_view(["GET", "POST"])
# def ai_competitors(request):
#     """
#     GET /api/ai/competitors/?company_id=<id>&top_n=10&min_score=0.25&limit=10&force=0&verbose=0
#       Optional:
#         - &company=<name> (resolve to id)
#         - &limit_articles=80
#         - &min_relevance=0.30

#     Behavior (same as card_trends):
#       - Source of truth: company_profiles.cards.competitors.
#       - If today (UTC) < next_refresh_at.date() and data exists -> return schema (unless force=1).
#       - Else:
#           * call competitors_run(company_id, ...)
#           * re-read schema and return
#           * (compat) if AI wrote cards.new_competitors.items, migrate -> cards.competitors.data
#           * (safety) ensure next_refresh_at exists (now + 7d)
#     """
#     db = get_mongo_db()

#     # ---- inputs (query first; allow POST body "company" fallback) ----
#     company_id   = (request.GET.get("company_id") or "").strip() or None
#     company_name = (request.GET.get("company") or "").strip() or None
#     force        = str(request.GET.get("force", "0")).strip().lower() in ("1", "true", "yes", "y", "on")

#     # numeric knobs
#     def _int(q, d): 
#         try: return int(request.GET.get(q, d))
#         except Exception: return d
#     def _float(q, d): 
#         try: return float(request.GET.get(q, d))
#         except Exception: return d
#     def _bool(q, d=False):
#         v = request.GET.get(q)
#         if v is None: return d
#         return str(v).strip().lower() in ("1","true","yes","y","on")

#     limit_articles = _int("limit_articles", 80)
#     min_relevance  = _float("min_relevance", 0.30)
#     top_n          = _int("top_n", 10)
#     min_score      = _float("min_score", 0.25)
#     verbose        = _bool("verbose", False)

#     # Backward-compat: POST body { "company": "Name" }
#     if not company_id and not company_name and request.method == "POST":
#         body = request.data or {}
#         company_name = (body.get("company") or "").strip() or None

#     # ---- resolve company ----
#     if not company_id and company_name:
#         doc = get_company_profile(name=company_name)
#         if not doc:
#             return Response({"error": f"Company '{company_name}' not found"}, status=404)
#         company_id = str(doc["_id"])
#     if not company_id:
#         return Response({"error": "company_id (or company name) is required"}, status=400)
#     if company_id and not company_name:
#         prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"name": 1})
#         if prof:
#             company_name = prof.get("name")

#     # ---- helper: read schema + respond ----
#     def _read_schema_and_respond():
#         fresh = db["company_profiles"].find_one(
#             {"_id": ObjectId(company_id)},
#             {"name": 1, "cards.competitors": 1, "cards.new_competitors": 1}
#         )
#         if not fresh:
#             return Response({"error": "company profile not found"}, status=404)

#         name = fresh.get("name") or company_name
#         cards = fresh.get("cards") or {}
#         comp  = (cards.get("competitors") or {})

#         # Prefer normalized 'data'; fall back to legacy 'items' (either on competitors or new_competitors)
#         data = comp.get("data")
#         if not data:
#             data = comp.get("items")
#         if not data:
#             data = (cards.get("new_competitors") or {}).get("items") or []

#         return Response(
#             {"company": name, "company_id": company_id, "count": len(data or []), "competitors": (data or [])[:top_n]},
#             status=200,
#         )

#     # ---- freshness check ----
#     prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards": 1})
#     cards = (prof or {}).get("cards") or {}
#     comp  = cards.get("competitors") or {}
#     next_refresh_at   = comp.get("next_refresh_at")
#     next_refresh_date = _parse_iso_to_date(next_refresh_at)
#     today_utc         = datetime.now(timezone.utc).date()

#     if (not force) and next_refresh_date and today_utc < next_refresh_date and (comp.get("data") or comp.get("items") or []):
#         return _read_schema_and_respond()

#     # ---- call AI runner (best-effort; runner may persist to new_competitors.items) ----
#     try:
#         # Expect you imported like:
#         #   try:
#         #       from AI.competitors.main_competitors import run as competitors_run
#         #   except Exception: competitors_run = None
#         if competitors_run is not None:
#             competitors_run(
#                 company_id=company_id,
#                 limit_articles=limit_articles,
#                 min_relevance=min_relevance,
#                 top_n=top_n,
#                 min_score=min_score,
#                 persist_card=True,     # let runner write to cards (new_competitors.items)
#                 verbose=verbose,
#             )
#     except Exception as e:
#         logger.warning("competitors_run failed; continuing with schema as-is. %s", e)

#     # ---- migrate if AI wrote to cards.new_competitors.items ----
#     fresh = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards": 1}) or {}
#     cards = fresh.get("cards") or {}
#     newc  = cards.get("new_competitors") or {}
#     items = newc.get("items") or []
#     need_migrate = bool(items)

#     if need_migrate:
#         now = datetime.now(timezone.utc)
#         block = {
#             "data": items[:top_n],                     # normalize as 'data'
#             "updated_at": _iso_z(now),
#             "next_refresh_at": _iso_z(now + timedelta(days=7)),
#         }
#         db["company_profiles"].update_one(
#             {"_id": ObjectId(company_id)},
#             {"$set": {"cards.competitors": block}}
#         )

#     # ---- safety: ensure next_refresh_at exists on competitors ----
#     cur = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards.competitors": 1}) or {}
#     cur_block = ((cur.get("cards") or {}).get("competitors") or {})
#     if not cur_block.get("next_refresh_at"):
#         now = datetime.now(timezone.utc)
#         db["company_profiles"].update_one(
#             {"_id": ObjectId(company_id)},
#             {"$set": {"cards.competitors.next_refresh_at": _iso_z(now + timedelta(days=7))}}
#         )

#     # ---- final: re-read + return ----
#     return _read_schema_and_respond()


@api_view(["GET"])
def ai_backlinks(request):
    """
    GET /api/ai/backlinks/?company_id=<id>&limit=50&no_llm=0&force=0
      Optional:
        - &company=<name> (resolve to id)
        - &min_relevance=0.3
        - &verbose=1
        - &force=1   -> bypass freshness and re-run AI

    Source of truth: company_profiles.cards.backlinks
    - If today (UTC) < next_refresh_at.date() and data exists -> return schema (unless force)
    - Else:
        * call backlinks_run(company_id, ...)
        * persist to cards.backlinks as {"data": [...], "updated_at", "next_refresh_at"}
        * (compat) if AI wrote {"items": [...]}, migrate to {"data": [...]}
        * (safety) ensure next_refresh_at exists (now+7d)
        * re-read schema and return
    """
    if backlinks_run is None:
        return Response({"error": "backlinks.run not available"}, status=500)

    db = get_mongo_db()

    # --- Inputs ---
    company_id   = (request.GET.get("company_id") or "").strip() or None
    company_name = (request.GET.get("company") or "").strip() or None
    force        = str(request.GET.get("force", "0")).strip().lower() in ("1", "true", "yes", "y", "on")

    # numeric/bool
    try:
        limit = int(request.GET.get("limit", 50))
    except Exception:
        limit = 50
    limit = max(1, min(limit, 200))

    try:
        min_relevance = float(request.GET.get("min_relevance", 0.30))
    except Exception:
        min_relevance = 0.30

    def _to_bool(v, default=False):
        if v is None:
            return default
        return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

    with_llm = not _to_bool(request.GET.get("no_llm"), default=False)
    verbose  = _to_bool(request.GET.get("verbose"), default=False)

    # --- Resolve company (prefer id; allow name) ---
    if not company_id and not company_name:
        return Response({"error": "company_id (or company name) is required"}, status=400)

    if not company_id and company_name:
        doc = get_company_profile(name=company_name)
        if not doc:
            return Response({"error": f"Company '{company_name}' not found"}, status=404)
        company_id = str(doc["_id"])

    if company_id and not company_name:
        prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"name": 1})
        if prof:
            company_name = prof.get("name")

    # --- Helper: read schema + respond ---
    def _read_schema_and_respond():
        fresh = db["company_profiles"].find_one(
            {"_id": ObjectId(company_id)},
            {"name": 1, "cards.backlinks": 1}
        )
        if not fresh:
            return Response({"error": "company profile not found"}, status=404)

        name = fresh.get("name") or company_name
        backlinks_card = ((fresh.get("cards") or {}).get("backlinks") or {})

        # prefer normalized 'data'; fall back to legacy 'items'
        data = backlinks_card.get("data")
        if not data:
            data = backlinks_card.get("items") or []
        data = (data or [])[:limit]

        return Response(
            {"company": name, "company_id": company_id, "count": len(data), "backlinks": data},
            status=200,
        )

    # --- Freshness check ---
    prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards.backlinks": 1})
    backlinks_card = ((prof or {}).get("cards") or {}).get("backlinks") or {}
    next_refresh_at = backlinks_card.get("next_refresh_at")
    next_refresh_date = _parse_iso_to_date(next_refresh_at)
    today_utc = datetime.now(timezone.utc).date()

    if (not force) and next_refresh_date and today_utc < next_refresh_date and (backlinks_card.get("data") or backlinks_card.get("items") or []):
        return _read_schema_and_respond()

    # --- Refresh path: call AI runner ---
    try:
        results = backlinks_run(
            company_id=company_id,               # runner expects id
            limit=limit,
            min_relevance=min_relevance,
            with_llm=with_llm,
            persist=False,                       # we persist below for consistency
            verbose=verbose,
        ) or []

        # If the runner returned data but didn’t persist → manually persist (normalized as 'data')
        if isinstance(results, list):
            now = datetime.now(timezone.utc)
            new_block = {
                "data": results[:limit],                 # normalize to 'data'
                "updated_at": _iso_z(now),
                "next_refresh_at": _iso_z(now + timedelta(days=7)),
            }
            db["company_profiles"].update_one(
                {"_id": ObjectId(company_id)},
                {"$set": {"cards.backlinks": new_block}}
            )
    except Exception as e:
        logger.warning("backlinks_run failed; continuing with schema as-is. %s", e)

    # --- Compatibility: migrate legacy 'items' -> 'data' if runner stored it that way ---
    fresh = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards": 1}) or {}
    cards = fresh.get("cards") or {}
    bl = cards.get("backlinks") or {}
    if bl.get("items") and not bl.get("data"):
        now = datetime.now(timezone.utc)
        migrate_block = {
            "data": bl.get("items")[:limit],
            "updated_at": bl.get("updated_at") or _iso_z(now),
            "next_refresh_at": bl.get("next_refresh_at") or _iso_z(now + timedelta(days=7)),
        }
        db["company_profiles"].update_one(
            {"_id": ObjectId(company_id)},
            {"$set": {"cards.backlinks": migrate_block}}
        )

    # --- Safety: ensure next_refresh_at exists ---
    cur = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards.backlinks": 1}) or {}
    cur_block = ((cur.get("cards") or {}).get("backlinks") or {})
    if not cur_block.get("next_refresh_at"):
        now = datetime.now(timezone.utc)
        db["company_profiles"].update_one(
            {"_id": ObjectId(company_id)},
            {"$set": {"cards.backlinks.next_refresh_at": _iso_z(now + timedelta(days=7))}}
        )

    # --- Final: re-read and return ---
    return _read_schema_and_respond()


# @api_view(["GET"])
# def ai_opportunities(request):
#     """
#     GET /api/ai/opportunities/?company=EcoDrive%20Motors&industry=Electric%20Vehicles&limit=20&min_relevance=0.4&verbose=0

#     Behavior (same as trending/ideas):
#       - Always return what's stored in company_profiles.cards.opportunities.
#       - If today (UTC) >= next_refresh_at.date() OR next_refresh_at missing:
#           * try opportunities_run(...) (best-effort; may persist itself)
#           * if it returns a list, manually persist into cards.opportunities
#             with updated_at and next_refresh_at = now + 7 days
#           * re-read from Mongo and return that.
#     """
#     if opportunities_run is None:
#         return Response({"error": "opportunities.run not available"}, status=500)

#     db = get_mongo_db()

#     # --- Inputs ---
#     company_id   = (request.GET.get("company_id") or "").strip() or None
#     company_name = (request.GET.get("company") or "").strip() or None
#     industry     = (request.GET.get("industry") or "").strip()

#     if not industry:
#         return Response({"error": "industry is required"}, status=400)
#     if not company_id and not company_name:
#         return Response({"error": "company_id (or company name) is required"}, status=400)

#     # Resolve company (support name or id)
#     if not company_id and company_name:
#         doc = get_company_profile(name=company_name)
#         if not doc:
#             return Response({"error": f"Company '{company_name}' not found"}, status=404)
#         company_id = str(doc["_id"])

#     if company_id and not company_name:
#         prof_name = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"name": 1})
#         if prof_name:
#             company_name = prof_name.get("name")

#     # ints/floats
#     try:
#         limit = int(request.GET.get("limit", 20))
#     except Exception:
#         limit = 20
#     limit = max(1, min(limit, 200))

#     try:
#         min_relevance = float(request.GET.get("min_relevance", 0.4))
#     except Exception:
#         min_relevance = 0.4

#     # bool
#     verbose = str(request.GET.get("verbose", "0")).strip().lower() in ("1", "true", "yes", "y", "on")

#     # --- Helper: read schema + respond ---
#     def _read_schema_and_respond():
#         fresh = db["company_profiles"].find_one(
#             {"_id": ObjectId(company_id)},
#             {"name": 1, "cards.opportunities": 1}
#         )
#         if not fresh:
#             return Response({"error": "company profile not found"}, status=404)
#         name = fresh.get("name") or company_name
#         opp_card = ((fresh.get("cards") or {}).get("opportunities") or {})
#         data = (opp_card.get("data") or [])[:limit]
#         return Response(
#             {
#                 "company": name,
#                 "company_id": company_id,
#                 "industry": industry,
#                 "count": len(data),
#                 "opportunities": data
#             },
#             status=200,
#         )

#     # --- Freshness check (same logic as trending/ideas) ---
#     prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"cards.opportunities": 1})
#     opp_card = ((prof or {}).get("cards") or {}).get("opportunities") or {}
#     next_refresh_at = opp_card.get("next_refresh_at")
#     next_refresh_date = _parse_iso_to_date(next_refresh_at)
#     today_utc = datetime.now(timezone.utc).date()

#     # If still fresh and has data → return schema
#     if next_refresh_date and today_utc < next_refresh_date and (opp_card.get("data") or []):
#         return _read_schema_and_respond()

#     # --- Refresh path: call AI runner (best-effort) ---
#     try:
#         # opportunities_run signature expects name, not id
#         results = opportunities_run(
#             company_name=company_name,
#             industry_name=industry,
#             limit=limit,
#             min_relevance=min_relevance,
#             verbose=verbose,
#         ) or []

#         # If the runner returned data but didn't persist, we persist here
#         if isinstance(results, list):
#             now = datetime.now(timezone.utc)
#             new_block = {
#                 "data": results[:limit],                  # list[dict] of opportunities
#                 "updated_at": _iso_z(now),
#                 "next_refresh_at": _iso_z(now + timedelta(days=7)),  # +7 days
#             }
#             db["company_profiles"].update_one(
#                 {"_id": ObjectId(company_id)},
#                 {"$set": {"cards.opportunities": new_block}}
#             )
#     except Exception as e:
#         logger.warning("opportunities_run failed; returning schema as-is. %s", e)

#     # --- Re-read schema and return source of truth ---
#     return _read_schema_and_respond()


@api_view(["GET"])
def ai_opportunities(request):
    """
    GET /api/ai/opportunities/?company_id=<id>&history_id=<id>&limit=20

    Behavior:
      1) Validate params; call AI.collection_card.opportunities.main_opportunities.run(company_id, history_id).
      2) If the runner persisted a card at company_profiles.cards.opportunities, read it back and return it.
      3) Otherwise return an acknowledgement that the run completed (or was invoked) with empty items.
    """
    # Ensure the runner is importable
    if opportunities_run is None:
        return Response({"error": "opportunities.run not available"}, status=500)

    db = get_mongo_db()

    company_id = (request.GET.get("company_id") or "").strip()
    history_id = (request.GET.get("history_id") or "").strip()

    if not company_id:
        return Response({"error": "company_id is required"}, status=400)
    if not history_id:
        return Response({"error": "history_id is required"}, status=400)

    # basic limit guard (only used when reading back any persisted data)
    try:
        limit = int(request.GET.get("limit", 20))
    except Exception:
        limit = 20
    limit = max(1, min(limit, 200))

    # Validate ObjectId shape early for clearer errors
    try:
        _ = ObjectId(company_id)
        _ = ObjectId(history_id)
    except Exception:
        return Response({"error": "company_id and history_id must be valid ObjectId strings"}, status=400)

    # Optional: get name for nicer payloads
    prof = db["company_profiles"].find_one({"_id": ObjectId(company_id)}, {"name": 1}) or {}
    company_name = prof.get("name")

    # ---- Call the AI runner (authoritative business logic) ----
    try:
        # Your runner signature: run(company_id: str, history_id: str)
        opportunities_run(company_id=company_id, history_id=history_id)
    except Exception as e:
        logger.exception("opportunities_run failed: %s", e)
        # Even if AI fails, fall through to attempt reading whatever exists
        # (keeps the endpoint resilient)

    # ---- Read back (if the runner persisted a card) ----
    fresh = db["company_profiles"].find_one(
        {"_id": ObjectId(company_id)},
        {"name": 1, "cards.opportunities": 1}
    ) or {}

    name = fresh.get("name") or company_name or None
    opp_card = ((fresh.get("cards") or {}).get("opportunities") or {})

    # --- Normalize various shapes the runner might write ---
    # Allowed shapes:
    # A) dict with "data": [...]
    # B) dict with "opportunities": [...]
    # C) dict with "items"/"list": [...]
    # D) directly a list (cards.opportunities = [...])
    if isinstance(opp_card, list):
        items = opp_card
        updated_at = None
        next_refresh_at = None
        schema_hint = "list"
    elif isinstance(opp_card, dict):
        items = (
            opp_card.get("data")
            or opp_card.get("opportunities")
            or opp_card.get("items")
            or opp_card.get("list")
            or []
        )
        updated_at = opp_card.get("updated_at")
        next_refresh_at = opp_card.get("next_refresh_at")
        schema_hint = f"dict_keys={list(opp_card.keys())}"
    else:
        items = []
        updated_at = None
        next_refresh_at = None
        schema_hint = type(opp_card).__name__

    # Log what we found to help debug schema mismatches
    try:
        logger.info("cards.opportunities schema: %s", schema_hint)
    except Exception:
        pass

    data = (items or [])[:limit]

    # If we have persisted data, return it; otherwise return an ack
    if data:
        return Response(
            {
                "company": name,
                "company_id": company_id,
                "history_id": history_id,
                "count": len(data),
                "opportunities": data,
                "updated_at": updated_at,
                "next_refresh_at": next_refresh_at,
            },
            status=200,
        )

    # No persisted data yet (runner printed/processed but didn’t write)
    return Response(
        {
            "company": name,
            "company_id": company_id,
            "history_id": history_id,
            "count": 0,
            "opportunities": [],
            "message": "opportunities.run invoked. No card data found yet.",
        },
        status=200,
    )




# --- Company profiles: create/update one ---
@api_view(["POST"])
def upsert_company(request):
    """
    POST /api/company/upsert/
    Body JSON:
    {
      "name": "EcoDrive Motors",               # required, unique by name
      "description": "EV manufacturer...",     # optional
      "competitors": ["Tesla", "BYD"]          # optional list[str]
    }

    Returns: the stored document (id, name, description, competitors, cards, created_at)
    """
    try:
        data = request.data or {}
        name = (data.get("name") or "").strip()
        desc = (data.get("description") or "").strip()
        comps = data.get("competitors", []) or []

        if not name:
            return Response({"error": "name is required"}, status=400)
        if not isinstance(comps, list):
            return Response({"error": "competitors must be a list of strings"}, status=400)

        # Re-use your existing helper (creates default cards & next_refresh_at)
        from .persist import upsert_company_profile, get_mongo_db
        upsert_company_profile({"name": name, "description": desc, "competitors": comps})

        # Read back and return
        db = get_mongo_db()
        doc = db["company_profiles"].find_one({"name": name})
        if not doc:
            return Response({"error": "failed to read back profile"}, status=500)

        return Response({
            "id": str(doc.get("_id")),
            "name": doc.get("name"),
            "description": doc.get("description"),
            "competitors": doc.get("competitors", []),
            "created_at": doc.get("created_at"),
            "cards": doc.get("cards", {}),
        }, status=200)

    except Exception as e:
        logger.exception("upsert_company error: %s", e)
        return Response({"error": str(e)}, status=500)


# --- Company profiles: list/search (frontend paginates UI-side if desired) ---
@api_view(["GET"])
def list_companies(request):
    """
    GET /api/companies/?q=&page=1&page_size=20&sort=name&order=asc

    - q: optional substring match on name/description (case-insensitive)
    - page/page_size: basic server-side paging (frontend can ignore and paginate client-side)
    - sort: one of name, created_at
    - order: asc|desc
    """
    try:
        db = get_mongo_db()

        q = (request.GET.get("q") or "").strip()
        try:
            page = max(1, int(request.GET.get("page", 1)))
        except Exception:
            page = 1
        try:
            page_size = max(1, min(100, int(request.GET.get("page_size", 20))))
        except Exception:
            page_size = 20

        sort_field = (request.GET.get("sort") or "name").strip()
        if sort_field not in {"name", "created_at"}:
            sort_field = "name"
        order = (request.GET.get("order") or "asc").strip().lower()
        order_val = 1 if order == "asc" else -1

        filt = {}
        if q:
            # case-insensitive regex OR on name/description
            filt = {
                "$or": [
                    {"name": {"$regex": q, "$options": "i"}},
                    {"description": {"$regex": q, "$options": "i"}},
                ]
            }

        total = db["company_profiles"].count_documents(filt)
        cursor = (
            db["company_profiles"]
            .find(filt)
            .sort(sort_field, order_val)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        items = []
        for d in cursor:
            items.append({
                "id": str(d.get("_id")),
                "name": d.get("name"),
                "description": d.get("description"),
                "competitors": d.get("competitors", []),
                "created_at": d.get("created_at"),
            })

        return Response({
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": items,
        }, status=200)

    except Exception as e:
        logger.exception("list_companies error: %s", e)
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
def get_company(request):
    """
    GET /api/company/?name=EcoDrive%20Motors   (optional name)
    Returns the latest (or named) company profile, including cards.
    """
    name = (request.GET.get("name") or "").strip() or None
    try:
        doc = get_company_profile(name=name)
        if not doc:
            return Response({"error": "company profile not found"}, status=404)

        # Sensible default cards in case you fetch an older doc without 'cards'
        def _default_cards():
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            next_week = now + timedelta(days=7)
            # Store as ISO8601 string with Z suffix for consistency in FE
            nx = next_week.isoformat().replace("+00:00", "Z")
            return {
                "trending":     {"data": [], "updated_at": None, "next_refresh_at": nx},
                "newsfeed":     {"data": [], "updated_at": None, "next_refresh_at": nx},
                "ideas":        {"data": [], "updated_at": None, "next_refresh_at": nx},
                "backlinks":    {"data": [], "updated_at": None, "next_refresh_at": nx},
                "opportunities":{"data": [], "updated_at": None, "next_refresh_at": nx},
                "new_competitors": {"data": [], "updated_at": None, "next_refresh_at": nx}, # ← NEW
            }

        cards = doc.get("cards") or _default_cards()

        return Response({
            "id": str(doc.get("_id")),
            "name": doc.get("name"),
            "description": doc.get("description"),
            "competitors": doc.get("competitors", []),
            "created_at": doc.get("created_at"),
            "cards": cards,
        }, status=200)
    except Exception as e:
        logger.exception("get_company error: %s", e)
        return Response({"error": str(e)}, status=500)