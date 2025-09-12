# Backend/api/views.py
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import FetchLog  # added FetchLog
# from .serializers import ProjectSerializer
from .fetchers import (
    fetch_reddit_rss,
    fetch_reddit_official,
    fetch_google_news,
    fetch_bbc_rss,
    fetch_techcrunch_rss,
    fetch_guardian_api,
    fetch_hackernews_api,
)
from .persist import persist_posts  # added persist helper

import logging
import json
logger = logging.getLogger(__name__)

def health(request):
    return JsonResponse({"status": "ok", "version": "v1"})

# Optional sample CRUD (kept commented to avoid missing model import)
# class ProjectCreateView(generics.CreateAPIView):
#     queryset = project.objects.all()
#     serializer_class = ProjectSerializer
# class ProjectListView(generics.ListAPIView):
#     queryset = project.objects.order_by("-id")
#     serializer_class = ProjectSerializer
# class ProjectDetailView(generics.RetrieveAPIView):
#     queryset = project.objects.all()
#     serializer_class = ProjectSerializer

# Map source keys -> fetcher callables
FETCHERS = {
    "reddit_official":  fetch_reddit_official, 
    "reddit_rss":       fetch_reddit_rss,
    "news_rss":         fetch_google_news,
    "bbc_rss":          fetch_bbc_rss,
    "techcrunch_rss":   fetch_techcrunch_rss,
    "guardian_api":     fetch_guardian_api,
    "hackernews_api":   fetch_hackernews_api,
    
}

def _parse_sources_param(val):
    """
    Accepts:
      - list: ["guardian_api","bbc_rss"]
      - csv string: "guardian_api,bbc_rss"
      - single string: "guardian_api"
    Returns a list of valid keys.
    """
    if not val:
        return []
    if isinstance(val, list):
        raw = val
    elif isinstance(val, str):
        raw = [s.strip() for s in val.split(",") if s.strip()]
    else:
        raw = []
    # keep only known fetchers, preserve order, de-dupe
    seen = set()
    out = []
    for k in raw:
        if k in FETCHERS and k not in seen:
            seen.add(k)
            out.append(k)
    return out

# /api/search (POST)
@api_view(["POST"])
def search_posts(request):
    """
    Improved MVP search v8 (Phase-2 + per-source & test mode):
      - NEW: choose sources via 'sources' or 'source' param.
      - NEW: 'persist': false to skip DB writes for testing.
      - Build upstream query from subject + optional location/industry.
      - Fetch from selected sources (default = all).
      - Interleave, dedupe by URL, freshness filter.
      - Relevance: subject is REQUIRED; title > body; location/industry boosts.
      - Sort by score desc, then recency desc.
      - Fetch pool size via 'fetch_limit' (default 30, 10..100).
      - Display cap HARD at 10 via 'limit' (1..10).
      - Persist (Phase-1 policy: save displayed only) unless persist=false.
      - Adds X-Sources-Used & X-Source-Counts debug headers.
    """
    data = request.data or {}
    subject  = (data.get("subject")  or "").strip()
    location = (data.get("location") or "").strip()
    industry = (data.get("industry") or "").strip()

    # ---- display cap (1..10) ----
    try:
        requested_limit = int(data.get("limit") or 10)
    except Exception:
        requested_limit = 10
    limit = max(1, min(requested_limit, 10))  # HARD cap

    # ---- fetch pool (10..100), default 30 ----
    try:
        fetch_limit = int(data.get("fetch_limit") or 30)
    except Exception:
        fetch_limit = 30
    fetch_limit = max(10, min(fetch_limit, 100))

    # ---- freshness window ----
    try:
        days = int(data.get("days") or 7)
    except Exception:
        days = 7

    # ---- testing knob: persist? (default True) ----
    persist_flag = True
    if isinstance(data.get("persist"), bool):
        persist_flag = data.get("persist")

    if not subject:
        return Response({"error": "subject is required"}, status=status.HTTP_400_BAD_REQUEST)

    # 1) Upstream query (helps sources pre-filter)
    query_terms = [subject]
    if location: query_terms.append(location)
    if industry: query_terms.append(industry)
    upstream_query = " ".join(query_terms)

    # 2) Choose sources
    selected = _parse_sources_param(data.get("sources") or data.get("source"))
    if not selected:
        selected = list(FETCHERS.keys())  # default: all
    # Fetch
    sources_data = []
    per_source_counts = {}  # before filtering/merge

    for key in selected:
        fn = FETCHERS[key]
        try:
            rows = fn(upstream_query, limit=fetch_limit)
        except Exception as e:
            logger.exception("%s error: %s", key, e)
            rows = []
        sources_data.append(rows)
        per_source_counts[key] = len(rows)

    # 3) Interleave (round-robin across selected sources)
    interleaved = []
    max_len = max((len(lst) for lst in sources_data), default=0)
    for i in range(max_len):
        for lst in sources_data:
            if i < len(lst):
                interleaved.append(lst[i])

    # 4) Dedupe by URL (first wins)
    seen = set()
    deduped = []
    for p in interleaved:
        u = p.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        deduped.append(p)

    # 5) Freshness window
    import time
    now = int(time.time())
    cutoff = now - days * 86400
    fresh = [p for p in deduped if (p.get("published_ts") or 0) >= cutoff] or deduped

    # 6) Relevance/scoring system (subject mandatory; title > body; boosts for location/industry)
    subj_l = subject.lower()
    loc_l  = location.lower()
    ind_l  = industry.lower()

    # hard filter: must contain the subject somewhere
    def relevance(p):
        title = (p.get("title") or "").lower()
        body  = (p.get("text")  or "").lower()
        hay   = f"{title} {body}"
        if subj_l and subj_l not in hay:
            return None

        score = 0
       # subject: title hit > body hit
        if subj_l in title:
            score += 3
        elif subj_l in body:
            score += 1

        # optional boosts
        if loc_l and loc_l in hay:
            score += 2
        if ind_l and ind_l in hay:
            score += 2
        return score

    scored = []
    for p in fresh:
        s = relevance(p)
        if s is not None:
            scored.append((s, p.get("published_ts") or 0, p))

    # If nothing matches the subject, return empty (no unrelated fallback)
    if not scored:
        logger.info("/api/search subject='%s' -> 0 posts (sources=%s)", subject, ",".join(selected))
        resp = Response([], status=200)
        resp["X-Results-Requested"] = str(requested_limit)
        resp["X-Results-Limit"] = str(limit)
        resp["X-Results-Returned"] = "0"
        resp["X-Fetch-Limit"] = str(fetch_limit)
        resp["X-Freshness-Days"] = str(days)
        resp["X-Sources-Used"] = ",".join(selected)
        # simple counts header like: key=cnt;key=cnt
        resp["X-Source-Counts"] = ";".join(f"{k}={per_source_counts.get(k,0)}" for k in selected)
        if persist_flag:
            try:
                FetchLog.objects.create(
                    subject=subject,
                    location=location,
                    industry=industry,
                    days=days,
                    limit=limit,
                    result_count=0
                )
            except Exception as e:
                logger.exception("fetchlog error: %s", e)
        return resp

    # 7) Sort by score desc, then recency desc; cap to display limit
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    result = [p for (_s, _ts, p) in scored][:limit]

    logger.info("/api/search subject='%s' -> %d posts (fetch_limit=%d; sources=%s)",
                subject, len(result), fetch_limit, ",".join(selected))

    # Persist only what we display + write fetch log (phase-1 policy), unless testing persist=false
    if persist_flag:
        try:
            created, updated = persist_posts(result)
            logger.info("persist: created=%d updated=%d", created, updated)
        except Exception as e:
            logger.exception("persist error: %s", e)

        try:
            FetchLog.objects.create(
                subject=subject,
                location=location,
                industry=industry,
                days=days,
                limit=limit,
                result_count=len(result)
            )
        except Exception as e:
            logger.exception("fetchlog error: %s", e)

    # Helpful headers
    resp = Response(result, status=200)
    resp["X-Results-Requested"] = str(requested_limit)
    resp["X-Results-Limit"] = str(limit)           # display cap
    resp["X-Results-Returned"] = str(len(result))
    resp["X-Fetch-Limit"] = str(fetch_limit)       # pool size used
    resp["X-Freshness-Days"] = str(days)
    resp["X-Sources-Used"] = ",".join(selected)
    resp["X-Source-Counts"] = ";".join(f"{k}={per_source_counts.get(k,0)}" for k in selected)
    return resp