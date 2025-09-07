# Backend/api/views.py
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import project
from .serializers import ProjectSerializer
from .fetchers import fetch_reddit_rss, fetch_google_news

import logging
logger = logging.getLogger(__name__)

def health(request):
    return JsonResponse({"status": "ok", "version": "v1"})

# existing model endpoints 
class ProjectCreateView(generics.CreateAPIView):
    queryset = project.objects.all()
    serializer_class = ProjectSerializer

class ProjectListView(generics.ListAPIView):
    queryset = project.objects.order_by("-id")
    serializer_class = ProjectSerializer

class ProjectDetailView(generics.RetrieveAPIView):
    queryset = project.objects.all()
    serializer_class = ProjectSerializer

# /api/search (POST)
@api_view(["POST"])
def search_posts(request):
    """
    Improved MVP search v3 (with hard cap = 10):
      - Build upstream query from subject + optional location/industry.
      - Fetch Reddit + Google News.
      - Interleave sources, dedupe by URL.
      - Freshness filter: last N days (default 7; override via 'days').
      - Relevance: subject is REQUIRED; title > body; location/industry add boosts.
      - Sort by score desc, then recency desc. No unrelated fallback.
      - Sponsor requirement: return at most 10 results (capped).
    """
    data = request.data or {}
    subject  = (data.get("subject")  or "").strip()
    location = (data.get("location") or "").strip()
    industry = (data.get("industry") or "").strip()

    # ---- hard cap on limit (1 - 10) ----
    try:
        requested_limit = int(data.get("limit") or 10)
    except Exception:
        requested_limit = 10
    limit = max(1, min(requested_limit, 10))

    try:
        days = int(data.get("days") or 7)  # override with {"days": 14} etc.
    except Exception:
        days = 7

    if not subject:
        return Response({"error": "subject is required"}, status=status.HTTP_400_BAD_REQUEST)

    # 1) Upstream query (helps sources pre-filter)
    query_terms = [subject]
    if location: query_terms.append(location)
    if industry: query_terms.append(industry)
    upstream_query = " ".join(query_terms)

    # 2) Fetch
    try:
        r_posts = fetch_reddit_rss(upstream_query, limit=limit)
    except Exception as e:
        logger.exception("reddit_rss error: %s", e)
        r_posts = []

    try:
        g_posts = fetch_google_news(upstream_query, limit=limit)
    except Exception as e:
        logger.exception("google_news error: %s", e)
        g_posts = []

    # 3) Interleave (r,g,r,g,r...) for variety
    interleaved = []
    for a, b in zip(r_posts, g_posts):
        interleaved.extend([a, b])
    if len(r_posts) > len(g_posts):
        interleaved.extend(r_posts[len(g_posts):])
    elif len(g_posts) > len(r_posts):
        interleaved.extend(g_posts[len(r_posts):])

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

    # 6) Relevance: SUBJECT IS MANDATORY; boosts for location/industry; title > body; newer breaks ties
    subj_l = subject.lower()
    loc_l  = location.lower()
    ind_l  = industry.lower()

    def relevance(p):
        title = (p.get("title") or "").lower()
        body  = (p.get("text")  or "").lower()
        hay   = f"{title} {body}"

        # hard filter: must contain the subject somewhere
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
        logger.info("/api/search subject='%s' -> 0 posts (strict subject filter)", subject)
        resp = Response([], status=200)
        resp["X-Results-Requested"] = str(requested_limit)
        resp["X-Results-Limit"] = str(limit)
        resp["X-Results-Returned"] = "0"
        return resp

    # 7) Sort by score desc, then recency desc; cap to limit
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    result = [p for (_s, _ts, p) in scored][:limit]

    logger.info("/api/search subject='%s' -> %d posts", subject, len(result))

    # Add helpful headers
    resp = Response(result, status=200)
    resp["X-Results-Requested"] = str(requested_limit)
    resp["X-Results-Limit"] = str(limit)
    resp["X-Results-Returned"] = str(len(result))
    return resp

