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
    Improved MVP search:
      - Build upstream query using subject + optional location/industry.
      - Fetch Reddit + Google News with that combined query.
      - Dedupe by URL and sort by recency.
      - Apply local text filters (AND).
      - If filters yield 0, gracefully fall back to unfiltered top items.
    """
    data = request.data or {}
    subject = (data.get("subject") or "").strip()
    location = (data.get("location") or "").strip()
    industry = (data.get("industry") or "").strip()
    try:
        limit = int(data.get("limit") or 10)
    except Exception:
        limit = 10

    if not subject:
        return Response({"error": "subject is required"}, status=status.HTTP_400_BAD_REQUEST)

    # 1) Build upstream query
    query_terms = [subject]
    if location:
        query_terms.append(location)
    if industry:
        query_terms.append(industry)
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

    # 3) Interleave sources (r,g,r,g…) to keep variety
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

    # 5) Sort by recency (published_ts desc)
    def ts(p):
        return p.get("published_ts") or 0
    deduped.sort(key=ts, reverse=True)

    # 6) Local AND-filters (optional)
    def matches_filters(p):
        hay = f"{p.get('title','')} {p.get('text','')}".lower()
        if location and location.lower() not in hay:
            return False
        if industry and industry.lower() not in hay:
            return False
        return True

    filtered = [p for p in deduped if matches_filters(p)]
    result = (filtered or deduped)[:limit]   # fallback to unfiltered if filtered is empty

    logger.info("/api/search subject='%s' -> %d posts", subject, len(result))
    return Response(result, status=200)

