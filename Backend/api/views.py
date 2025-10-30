# # Backend/api/views.py
# from django.http import JsonResponse
# from rest_framework import status
# from rest_framework.decorators import api_view
# from rest_framework.response import Response

# import logging, time
# from bson import ObjectId
# from threading import Thread

# from .analytics import trend_timeseries_by_day, trend_top_tags, trend_by_source
# from .analytics import global_top_topics

# from .sources import REGISTRY as FETCHERS
# from .persist import (
#     get_mongo_db,
#     create_history,
#     persist_raw_insights,
#     seed_ai_result_stubs,
#     get_company_profile,
#     mark_history_ai_started,
#     mark_history_ai_progress,
#     mark_history_ai_done,
#     write_ai_results_batch,
# )

# logger = logging.getLogger(__name__)

# # -------------------- Optional: import external AI runner --------------------
# try:
#     # expects: def run(history_id: str, keyword: str) -> Any
#     from AI.ranking_algorithm.main import run as external_ai_run
#     logger.info("Imported external AI runner: AI.ranking_algorithm.main.run")
# except Exception as _e:
#     external_ai_run = None
#     logger.warning("AI.main.run not importable; will use built-in fallback worker.")

# # -------------------- Optional: import card analyzers ------------------------
# try:
#     # News card analyzer
#     from AI.collection_card.news_feed import analyse_news_relevancy
# except Exception:
#     analyse_news_relevancy = None
#     logger.warning("AI.collection_card.news_feed.analyse_news_relevancy not importable.")

# try:
#     # Trending topics analyzer
#     from AI.collection_card.trending_topics import analyse_relevancy
# except Exception:
#     analyse_relevancy = None
#     logger.warning("AI.collection_card.trending_topics.analyse_relevancy not importable.")

# # (Optional) fetch helpers if AI team provided them; we guard usage below.
# try:
#     from AI.collection_card.news_feed import fetch_news
# except Exception:
#     fetch_news = None
# try:
#     # NOTE: fetch_trends is under trending_topics, not news_feed.
#     from AI.collection_card.trending_topics import fetch_trends
# except Exception:
#     fetch_trends = None


# def health(request):
#     return JsonResponse({"status": "ok", "version": "v1"})

# def _parse_sources_param(val):
#     if not val:
#         return []
#     if isinstance(val, list):
#         raw = val
#     elif isinstance(val, str):
#         raw = [s.strip() for s in val.split(",") if s.strip()]
#     else:
#         raw = []
#     seen = set()
#     out = []
#     for k in raw:
#         if k in FETCHERS and k not in seen:
#             seen.add(k)
#             out.append(k)
#     return out

# # -------------------- Built-in simple AI worker (fallback) -------------------
# def _process_history_async(history_id: ObjectId, subject: str, batch_size: int = 50):
#     """
#     Minimal fallback that marks started and attempts to let external AI handle,
#     otherwise marks done with whatever exists.
#     """
#     db = get_mongo_db()
#     mark_history_ai_started(history_id)
#     try:
#         if external_ai_run:
#             external_ai_run(str(history_id), subject)
#         total = db["ai_results"].count_documents(
#             {"history_id": ObjectId(history_id), "status": "done"}
#         )
#         mark_history_ai_done(history_id, total_count=total)
#     except Exception as e:
#         logger.exception("AI worker failed for history=%s: %s", history_id, e)

# # -------------------- External AI kicker (prefers AI.main.run) ---------------
# def _kick_external_ai(history_id: ObjectId, subject: str):
#     """
#     Fire the AI team's pipeline in-process without blocking the request.
#     If AI module isn't importable or raises, fall back to the built-in worker.
#     """
#     db = get_mongo_db()
#     try:
#         mark_history_ai_started(history_id)

#         if not external_ai_run:
#             logger.warning("AI.main.run unavailable; using fallback worker.")
#             _process_history_async(history_id, subject)
#             return

#         external_ai_run(str(history_id), subject)

#         total = db["ai_results"].count_documents(
#             {"history_id": ObjectId(history_id), "status": "done"}
#         )
#         mark_history_ai_progress(history_id, total)
#         mark_history_ai_done(history_id, total_count=total)
#         logger.info("External AI finished for history=%s, produced=%s items.", history_id, total)

#     except Exception as e:
#         logger.exception("External AI run failed; falling back. %s", e)
#         _process_history_async(history_id, subject)

# # -------------------- Search + ingest --------------------
# @api_view(["POST"])
# def search_posts(request):
#     """
#     Pipeline:
#       - Create a history record.
#       - For each selected source, fetch (default 120).
#       - Interleave, dedupe by URL, apply freshness window.
#       - Persist into raw_insights.
#       - Seed ai_results stubs (status='queued') for this history_id.
#       - Kick external AI (or fallback worker) in a thread.
#       - Return preview + history_id.
#     """
#     data = request.data or {}
#     subject  = (data.get("subject")  or "").strip()
#     location = (data.get("location") or "").strip()
#     industry = (data.get("industry") or "").strip()

#     if not subject:
#         return Response({"error": "subject is required"}, status=status.HTTP_400_BAD_REQUEST)

#     try:
#         preview_limit = int(data.get("limit") or 10)
#     except Exception:
#         preview_limit = 10
#     preview_limit = max(1, min(preview_limit, 10))

#     try:
#         fetch_limit = int(data.get("fetch_limit") or 120)
#     except Exception:
#         fetch_limit = 120
#     fetch_limit = max(10, min(fetch_limit, 200))

#     try:
#         persist_pool_limit = int(data.get("persist_pool_limit") or 500)
#     except Exception:
#         persist_pool_limit = 500
#     persist_pool_limit = max(50, min(persist_pool_limit, 2000))

#     try:
#         days = int(data.get("days") or 7)
#     except Exception:
#         days = 7

#     selected = _parse_sources_param(data.get("sources") or data.get("source"))
#     if not selected:
#         selected = list(FETCHERS.keys())

#     query_terms = [subject]
#     if location: query_terms.append(location)
#     if industry: query_terms.append(industry)
#     upstream_query = " ".join(query_terms)

#     history_id = create_history(
#         subject=subject,
#         location=location,
#         industry=industry,
#         sources_used=selected,
#         params={
#             "days": days,
#             "fetch_limit": fetch_limit,
#             "persist_pool_limit": persist_pool_limit,
#         },
#         ai_target=100,
#     )

#     sources_data = []
#     per_source_counts = {}
#     for key in selected:
#         fn = FETCHERS[key]
#         try:
#             rows = fn(upstream_query, limit=fetch_limit)
#         except Exception as e:
#             logger.exception("%s error: %s", key, e)
#             rows = []
#         sources_data.append(rows)
#         per_source_counts[key] = len(rows)

#     interleaved = []
#     max_len = max((len(lst) for lst in sources_data), default=0)
#     for i in range(max_len):
#         for lst in sources_data:
#             if i < len(lst):
#                 interleaved.append(lst[i])

#     seen = set()
#     deduped = []
#     for p in interleaved:
#         u = (p.get("url") or "").strip()
#         if not u or u in seen:
#             continue
#         seen.add(u)
#         deduped.append(p)

#     now = int(time.time())
#     cutoff = now - days * 86400
#     fresh = [p for p in deduped if (p.get("published_ts") or 0) >= cutoff] or deduped

#     to_persist = fresh[:persist_pool_limit]
#     created, updated = persist_raw_insights(to_persist)
#     logger.info(
#         "raw_insights persisted: created=%d updated=%d (pool=%d)",
#         created, updated, len(to_persist)
#     )

#     seeded = seed_ai_result_stubs(history_id, to_persist)

#     Thread(
#         target=_kick_external_ai if external_ai_run else _process_history_async,
#         args=(history_id, subject),
#         daemon=True
#     ).start()

#     subj_l = subject.lower()
#     def score_row(p):
#         title = (p.get("title") or "").lower()
#         body  = (p.get("text")  or "").lower()
#         hay   = f"{title} {body}"
#         if subj_l and subj_l not in hay:
#             return None
#         score = 3 if subj_l in title else (1 if subj_l in body else 0)
#         return (score, p.get("published_ts") or 0)

#     scored = []
#     for p in fresh:
#         s = score_row(p)
#         if s is not None:
#             scored.append((s[0], s[1], p))
#     scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
#     preview = [p for (_s, _ts, p) in scored][:preview_limit]

#     resp = Response({
#         "history_id": str(history_id),
#         "preview": preview,
#         "counts": {
#             "per_source": per_source_counts,
#             "fetched_total": sum(per_source_counts.values()),
#             "deduped": len(deduped),
#             "fresh": len(fresh),
#             "persisted": len(to_persist),
#             "seeded_ai_results": seeded,
#         }
#     }, status=200)
#     resp["X-Sources-Used"] = ",".join(selected)
#     resp["X-Fetch-Limit"] = str(fetch_limit)
#     resp["X-Persist-Pool-Limit"] = str(persist_pool_limit)
#     resp["X-Freshness-Days"] = str(days)
#     return resp

# # -------------------- NEW READ ENDPOINTS --------------------
# @api_view(["GET"])
# def list_history(request):
#     try:
#         db = get_mongo_db()
#         limit = int(request.GET.get("limit", 20))
#         limit = max(1, min(limit, 100))
#         ai_ready_param = request.GET.get("ai_ready")
#         filt = {}
#         if ai_ready_param:
#             filt["ai_ready"] = ai_ready_param.lower() == "true"

#         docs = list(db["history"].find(filt).sort("created_at", -1).limit(limit))
#         out = []
#         for d in docs:
#             out.append({
#                 "history_id": str(d["_id"]),
#                 "subject": d.get("subject"),
#                 "location": d.get("location"),
#                 "industry": d.get("industry"),
#                 "sources_used": d.get("sources_used", []),
#                 "created_at": d.get("created_at"),
#                 "ai_ready": d.get("ai_ready", False),
#                 "ai_count": d.get("ai_count", 0),
#                 "ai_target": d.get("ai_target", 100),
#             })
#         return Response(out, status=200)
#     except Exception as e:
#         logger.exception("list_history error: %s", e)
#         return Response({"error": str(e)}, status=500)

# @api_view(["GET"])
# def get_search_status(request):
#     hid = request.GET.get("history_id")
#     if not hid:
#         return Response({"error": "history_id is required"}, status=400)
#     try:
#         db = get_mongo_db()
#         doc = db["history"].find_one({"_id": ObjectId(hid)})
#         if not doc:
#             return Response({"error": "not found"}, status=404)
#         return Response({
#             "history_id": str(doc["_id"]),
#             "subject": doc.get("subject"),
#             "ai_ready": doc.get("ai_ready", False),
#             "ai_count": doc.get("ai_count", 0),
#             "ai_target": doc.get("ai_target", 100),
#             "created_at": doc.get("created_at"),
#             "finished_at": doc.get("finished_at"),
#         }, status=200)
#     except Exception as e:
#         logger.exception("get_search_status error: %s", e)
#         return Response({"error": str(e)}, status=500)

# @api_view(["GET"])
# def get_trends(request):
#     hid = request.GET.get("history_id")
#     if not hid:
#         return Response({"error": "history_id is required"}, status=400)
#     try:
#         days = int(request.GET.get("days", 30))
#     except Exception:
#         days = 30

#     try:
#         oid = ObjectId(hid)
#         return Response({
#             "history_id": hid,
#             "window_days": days,
#             "timeseries": trend_timeseries_by_day(oid, days),
#             "top_tags": trend_top_tags(oid, days, top_k=20),
#             "by_source": trend_by_source(oid, days),
#         }, status=200)
#     except Exception as e:
#         logger.exception("get_trends error: %s", e)
#         return Response({"error": str(e)}, status=500)

# @api_view(["GET"])
# def get_results(request):
#     hid = request.GET.get("history_id")
#     if not hid:
#         return Response({"error": "history_id is required"}, status=400)
#     try:
#         status_filter = (request.GET.get("status") or "done").strip().lower()
#         page = int(request.GET.get("page", 1))
#         page_size = int(request.GET.get("page_size", 10))
#         page = max(1, page)
#         page_size = max(1, min(page_size, 50))
#     except Exception:
#         status_filter = "done"
#         page, page_size = 1, 10

#     try:
#         db = get_mongo_db()
#         q = {"history_id": ObjectId(hid)}
#         if status_filter:
#             q["status"] = status_filter

#         cursor = db["ai_results"].find(q).sort("rank", 1).skip((page - 1) * page_size).limit(page_size)
#         docs = list(cursor)
#         total = db["ai_results"].count_documents(q)
#         out = []
#         for d in docs:
#             out.append({
#                 "rank": d.get("rank"),
#                 "url": d.get("url"),
#                 "ai_title": d.get("ai_title"),
#                 "ai_summary": d.get("ai_summary"),
#                 "tags": d.get("tags"),
#                 "relevance_score": d.get("relevance_score"),
#                 "published_ts": d.get("published_ts"),
#                 "source": d.get("source"),
#                 "status": d.get("status"),
#             })
#         return Response({
#             "history_id": hid,
#             "page": page,
#             "page_size": page_size,
#             "total": total,
#             "results": out
#         }, status=200)
#     except Exception as e:
#         logger.exception("get_results error: %s", e)
#         return Response({"error": str(e)}, status=500)

# # -------------------- Cards: Company-aware News -------------------------------
# def _build_company_context(name_param: str | None, id_param: str | None = None):
#     """
#     Load a company profile by id (preferred) or name (fallback), else latest.
#     Returns (company_name, description, competitors_list).
#     """
#     db = get_mongo_db()
#     doc = None

#     # 1) Prefer company_id if provided
#     if id_param:
#         try:
#             oid = ObjectId(id_param)
#             doc = db["company_profiles"].find_one({"_id": oid})
#         except Exception:
#             pass  # fallback to name/latest

#     # 2) Try by name
#     if not doc and name_param:
#         doc = get_company_profile(name=name_param)

#     # 3) Fallback to latest profile
#     if not doc:
#         doc = get_company_profile()

#     if not doc:
#         raise ValueError("No company profile available. Seed one first.")

#     return (doc.get("name"), doc.get("description") or "", doc.get("competitors") or [])


# @api_view(["GET"])
# def card_news(request):
#     """
#     GET /api/cards/news/?company_id=<id>&threshold=0.5&limit=10
#     or /api/cards/news/?company=EcoDrive%20Motors
#     Optional: &api_url=https://...  (if AI team wants to fetch news via external API)
#     Returns: { company, count, items: [{ title, url, relevance, source, published_date }] }
#     """
#     if analyse_news_relevancy is None:
#         return Response({"error": "news analyzer not available"}, status=500)

#     company_name = (request.GET.get("company") or "").strip() or None
#     company_id = (request.GET.get("company_id") or "").strip() or None
#     api_url = (request.GET.get("api_url") or "").strip() or None

#     try:
#         threshold = float(request.GET.get("threshold", 0.5))
#     except Exception:
#         threshold = 0.5
#     try:
#         limit = int(request.GET.get("limit", 10))
#     except Exception:
#         limit = 10
#     limit = max(1, min(limit, 50))

#     try:
#         # Build company context (prefer id)
#         cname, description, competitors = _build_company_context(company_name, company_id)
#         context = {
#             "company": cname,
#             "description": description,
#             "competitors": competitors,
#             "recent_searches": [],
#         }

#         # Get news articles: external API if given, else fallback to raw_insights
#         news_articles = []
#         if api_url and fetch_news:
#             try:
#                 news_articles = fetch_news.get_news_articles(api_url)
#             except Exception as fe:
#                 logger.exception("fetch_news failed: %s", fe)

#         if not news_articles:
#             db = get_mongo_db()
#             cursor = (
#                 db["raw_insights"]
#                 .find({}, {"title": 1, "url": 1, "source": 1, "published_ts": 1, "text": 1})
#                 .sort("published_ts", -1)
#                 .limit(200)
#             )
#             for r in cursor:
#                 news_articles.append({
#                     "title": r.get("title") or "",
#                     "url": r.get("url") or "",
#                     "source": r.get("source"),
#                     "published_date": r.get("published_ts"),
#                     "text": r.get("text") or "",
#                 })

#         analysis_result = analyse_news_relevancy.news_relevancy_rag(context, news_articles)
#         filtered = [it for it in analysis_result if float(it.get("relevance", 0)) >= threshold]
#         if limit:
#             filtered = filtered[:limit]

#         out = [{
#             "title": it.get("title"),
#             "url": it.get("url"),
#             "relevance": it.get("relevance"),
#             "source": it.get("source"),
#             "published_date": it.get("published_date"),
#         } for it in filtered]

#         return Response({"company": cname, "count": len(out), "items": out}, status=200)

#     except Exception as e:
#         logger.exception("card_news error: %s", e)
#         return Response({"error": str(e)}, status=500)


# # -------------------- Cards: Company-aware Trending Topics --------------------
# @api_view(["GET"])
# def card_trends(request):
#     """
#     GET /api/cards/trending/?company_id=<id>&threshold=0.5&limit=10
#     or /api/cards/trending/?company=EcoDrive%20Motors
#     Optional: &api_url=https://... (if AI team wants to fetch trending topics externally)
#     Returns: [ "EV charging", "battery recycling", ... ]
#     """
#     if analyse_relevancy is None:
#         return Response({"error": "topic analyzer not available"}, status=500)

#     company_name = (request.GET.get("company") or "").strip() or None
#     company_id = (request.GET.get("company_id") or "").strip() or None
#     api_url = (request.GET.get("api_url") or "").strip() or None

#     try:
#         threshold = float(request.GET.get("threshold", 0.5))
#     except Exception:
#         threshold = 0.5
#     try:
#         limit = int(request.GET.get("limit", 10))
#     except Exception:
#         limit = 10
#     limit = max(1, min(limit, 50))

#     try:
#         # Build company context (prefer id)
#         cname, description, competitors = _build_company_context(company_name, company_id)
#         context = {
#             "company": cname,
#             "description": description,
#             "competitors": competitors,
#             "recent_searches": [],
#         }

#         # Get trending topics: external API if given, else fallback
#         trending_topics = []
#         if api_url and fetch_trends:
#             try:
#                 trending_topics = fetch_trends.get_trending_topics(api_url)
#             except Exception as fe:
#                 logger.exception("fetch_trends failed: %s", fe)

#         if not trending_topics:
#             trending_topics = global_top_topics(days=30, limit=30)

#         # Run AI relevance
#         analysis = analyse_relevancy.relevancy_rag(context, trending_topics)
#         filtered = [
#             x.get("topic")
#             for x in analysis
#             if float(x.get("relevance", 0)) >= threshold
#         ]
#         if limit:
#             filtered = filtered[:limit]

#         # ✅ Return as a simple list
#         return Response(filtered, status=200)

#     except Exception as e:
#         logger.exception("card_trends error: %s", e)
#         return Response({"error": str(e)}, status=500)

# # -------------------- Debug --------------------
# @api_view(["GET"])
# def mongo_status(request):
#     try:
#         db = get_mongo_db()
#         names = sorted(db.list_collection_names())
#         counts = {}
#         for c in ["raw_insights", "ai_results", "history"]:
#             if c in names:
#                 counts[c] = db[c].count_documents({})
#         return Response({"db": db.name, "collections": names, "counts": counts}, status=200)
#     except Exception as e:
#         return Response({"error": str(e)}, status=500)

# @api_view(["GET"])
# def get_top_topics(request):
#     """
#     GET /api/topics/top?days=30&limit=15
#     Returns a simple list of trending topic tags.
#     """
#     days = int(request.GET.get("days", 30))
#     limit = int(request.GET.get("limit", 15))
#     try:
#         data = global_top_topics(days=days, limit=limit)
#         return Response({"window_days": days, "topics": data}, status=200)
#     except Exception as e:
#         logger.exception("get_top_topics error: %s", e)
#         return Response({"error": str(e)}, status=500)

# @api_view(["GET"])
# def get_company(request):
#     """
#     GET /api/company/?name=EcoDrive%20Motors   (optional name)
#     Returns the latest (or named) company profile.
#     """
#     name = (request.GET.get("name") or "").strip() or None
#     try:
#         doc = get_company_profile(name=name)
#         if not doc:
#             return Response({"error": "company profile not found"}, status=404)
#         return Response({
#             "id": str(doc.get("_id")),
#             "name": doc.get("name"),
#             "description": doc.get("description"),
#             "competitors": doc.get("competitors", []),
#             "created_at": doc.get("created_at"),
#         }, status=200)
#     except Exception as e:
#         logger.exception("get_company error: %s", e)
#         return Response({"error": str(e)}, status=500)



# Backend/api/views.py
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

import logging, time, json
from bson import ObjectId
from threading import Thread

from .analytics import trend_timeseries_by_day, trend_top_tags, trend_by_source
from .analytics import global_top_topics
from .analytics import get_recent_articles

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

# -----------------------------------------------------------------------------
# Optional AI imports
# -----------------------------------------------------------------------------
try:
    # expects: def run(history_id: str, keyword: str) -> Any
    from AI.ranking_algorithm.main import run as external_ai_run
except Exception:
    external_ai_run = None
    logger.warning("AI.ranking_algorithm.main.run not importable; will use fallback worker.")

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
    from AI.collection_card.ideas.generate_actionable_insights import generate_actionable_insights
except Exception:
    generate_actionable_insights = None
    logger.warning("AI.collection_card.ideas.generate_actionable_insights not importable.")


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


def _coerce_ai_list(value):
    """
    Accepts:
      - Python list (already parsed) -> returns list
      - JSON string of a list       -> parses & returns list
      - plain error string          -> raises ValueError with that string
      - anything else               -> raises ValueError with type info
    """
    if isinstance(value, list):
        return value

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValueError("AI returned empty response")
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as e:
                raise ValueError(f"AI returned malformed JSON: {e}")
            if not isinstance(parsed, list):
                raise ValueError(f"AI returned {type(parsed)}, expected list")
            return parsed
        # treat as plain-text error
        raise ValueError(raw[:500])

    raise ValueError(f"AI returned {type(value)}, expected list or JSON string")


def _build_company_context(name_param: str | None, id_param: str | None = None):
    """
    Resolve company by id (preferred) or name (fallback) or latest.
    Returns (company_name, description, competitors_list).
    """
    db = get_mongo_db()
    doc = None

    # 1) Prefer company_id if provided
    if id_param:
        try:
            oid = ObjectId(id_param)
            doc = db["company_profiles"].find_one({"_id": oid})
        except Exception:
            pass  # fall through

    # 2) Try by name
    if not doc and name_param:
        doc = get_company_profile(name=name_param)

    # 3) Fallback to latest
    if not doc:
        doc = get_company_profile()

    if not doc:
        raise ValueError("No company profile available. Seed one first.")

    return (doc.get("name"), doc.get("description") or "", doc.get("competitors") or [])


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
    Pipeline:
      - Create a history record.
      - For each selected source, fetch (default 120).
      - Interleave, dedupe by URL, apply freshness window.
      - Persist up to persist_pool_limit into raw_insights (global cache).
      - Seed ai_results stubs (status='queued') for this history_id.
      - Kick external AI (or fallback worker) in a thread.
      - Return preview (first 10) + history_id for FE.
    """
    data = request.data or {}
    subject  = (data.get("subject")  or "").strip()
    location = (data.get("location") or "").strip()
    industry = (data.get("industry") or "").strip()

    if not subject:
        return Response({"error": "subject is required"}, status=status.HTTP_400_BAD_REQUEST)

    # display preview cap (1..10)
    try:
        preview_limit = int(data.get("limit") or 10)
    except Exception:
        preview_limit = 10
    preview_limit = max(1, min(preview_limit, 10))

    # per-source fetch amount (increase pool)
    try:
        fetch_limit = int(data.get("fetch_limit") or 120)
    except Exception:
        fetch_limit = 120
    fetch_limit = max(10, min(fetch_limit, 200))

    # total to persist into raw_insights
    try:
        persist_pool_limit = int(data.get("persist_pool_limit") or 500)
    except Exception:
        persist_pool_limit = 500
    persist_pool_limit = max(50, min(persist_pool_limit, 2000))

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

    # Simple relevance gate for preview: must contain subject in title/body
    subj_l = subject.lower()
    def score_row(p):
        title = (p.get("title") or "").lower()
        body  = (p.get("text")  or "").lower()
        hay   = f"{title} {body}"
        if subj_l and subj_l not in hay:
            return None
        score = 3 if subj_l in title else (1 if subj_l in body else 0)
        return (score, p.get("published_ts") or 0)

    scored = []
    for p in fresh:
        s = score_row(p)
        if s is not None:
            scored.append((s[0], s[1], p))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    preview = [p for (_s, _ts, p) in scored][:preview_limit]

    resp = Response({
        "history_id": str(history_id),
        "preview": preview,
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
    hid = request.GET.get("history_id")
    if not hid:
        return Response({"error": "history_id is required"}, status=400)
    try:
        status_filter = (request.GET.get("status") or "done").strip().lower()
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        page = max(1, page)
        page_size = max(1, min(page_size, 50))
    except Exception:
        status_filter = "done"
        page, page_size = 1, 10

    try:
        db = get_mongo_db()
        q = {"history_id": ObjectId(hid)}
        if status_filter:
            q["status"] = status_filter

        cursor = db["ai_results"].find(q).sort("rank", 1).skip((page - 1) * page_size).limit(page_size)
        docs = list(cursor)
        total = db["ai_results"].count_documents(q)
        out = []
        for d in docs:
            out.append({
                "rank": d.get("rank"),
                "url": d.get("url"),
                "ai_title": d.get("ai_title"),
                "ai_summary": d.get("ai_summary"),
                "tags": d.get("tags"),
                "relevance_score": d.get("relevance_score"),
                "published_ts": d.get("published_ts"),
                "source": d.get("source"),
                "status": d.get("status"),
            })
        return Response({
            "history_id": hid,
            "page": page,
            "page_size": page_size,
            "total": total,
            "results": out
        }, status=200)
    except Exception as e:
        logger.exception("get_results error: %s", e)
        return Response({"error": str(e)}, status=500)


# -----------------------------------------------------------------------------
# Cards: Company-aware Trending Topics (primary endpoint for FE)
# -----------------------------------------------------------------------------
@api_view(["GET"])
def card_trends(request):
    """
    GET /api/cards/trending/?company_id=<id>&threshold=0.5&limit=10&full=0
    Optional:
      - &company=<name> (if you don't have company_id; we resolve it to an ID)
      - &api_url=<endpoint that returns topics or {"topics":[...]}>

    Returns:
      - full=0 (default): ["topic A", "topic B", ...]
      - full=1: [{"topic": "...", "relevance": 0.87}, ...]
    """
    if trending_run is None:
        return Response({"error": "trending.run not available"}, status=500)

    company_id   = (request.GET.get("company_id") or "").strip() or None
    company_name = (request.GET.get("company") or "").strip() or None
    api_url      = (request.GET.get("api_url") or "").strip() or None

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
        # Resolve company_id by name if needed
        if not company_id and company_name:
            doc = get_company_profile(name=company_name)
            if not doc:
                return Response({"error": f"Company '{company_name}' not found"}, status=404)
            company_id = str(doc["_id"])

        if not company_id:
            return Response({"error": "company_id (or company name) is required"}, status=400)

        # Default API for topics if not provided (ask for a bigger pool than limit)
        if not api_url:
            api_url = f"http://127.0.0.1:8001/api/topics/top/?days=30&limit={max(30, limit)}"

        # 🔥 Call your AI module's main run()
        results = trending_run(
            company_id=company_id,
            api_url=api_url,
            threshold=threshold,
            full_analysis=full,
            verbose=False,
            limit=limit,  # your run() already trims to limit
        )

        # Just in case the runner didn't trim:
        if isinstance(results, list):
            results = results[:limit]

        return Response(results, status=200)

    except Exception as e:
        logger.exception("card_trends error: %s", e)
        return Response({"error": str(e)}, status=500)

    
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


# -----------------------------------------------------------------------------
# Cards: Company-aware News (optional, for parity/testing)
# -----------------------------------------------------------------------------
@api_view(["GET"])
def card_news(request):
    """
    GET /api/cards/news/?company_id=<id>&threshold=0.5&limit=10
    Returns: { company, count, items: [{ title, url, relevance, source, published_date }] }
    """
    if analyse_news_relevancy is None:
        return Response({"error": "news analyzer not available"}, status=500)

    company_name = (request.GET.get("company") or "").strip() or None
    company_id = (request.GET.get("company_id") or "").strip() or None

    try:
        threshold = float(request.GET.get("threshold", 0.5))
    except Exception:
        threshold = 0.5
    try:
        limit = int(request.GET.get("limit", 10))
    except Exception:
        limit = 10
    limit = max(1, min(limit, 50))

    try:
        # Build company context
        cname, description, competitors = _build_company_context(company_name, company_id)
        context = {
            "company": cname,
            "description": description,
            "competitors": competitors,
            "recent_searches": [],
        }

        # Pull recent news from raw_insights (no external HTTP)
        db = get_mongo_db()
        cursor = (
            db["raw_insights"]
            .find({}, {"title": 1, "url": 1, "source": 1, "published_ts": 1, "text": 1})
            .sort("published_ts", -1)
            .limit(200)
        )
        news_articles = []
        for r in cursor:
            news_articles.append({
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "source": r.get("source"),
                "published_date": r.get("published_ts"),
                "text": r.get("text") or "",
            })

        # AI analysis
        analysis_raw = analyse_news_relevancy.news_relevancy_rag(context, news_articles)
        analysis_list = _coerce_ai_list(analysis_raw)

        filtered = [it for it in analysis_list if float(it.get("relevance", 0)) >= threshold]
        if limit:
            filtered = filtered[:limit]

        out = [{
            "title": it.get("title"),
            "url": it.get("url"),
            "relevance": it.get("relevance"),
            "source": it.get("source"),
            "published_date": it.get("published_date"),
        } for it in filtered]

        return Response({"company": cname, "count": len(out), "items": out}, status=200)

    except ValueError as e:
        logger.warning("card_news validation/AI error: %s", e)
        return Response({"error": str(e)}, status=502)
    except Exception as e:
        logger.exception("card_news error: %s", e)
        return Response({"error": str(e)}, status=500)


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

@api_view(["GET"])
def ai_generate_ideas(request):
    """
    GET /api/ai/ideas/?company=EcoDrive%20Motors&type=all&limit=10
    Generate actionable AI insights (content, opportunities, threats, etc.)
    """
    company_name = (request.GET.get("company") or "").strip()
    insight_type = request.GET.get("type", "all").lower()
    limit = int(request.GET.get("limit", 10))

    try:
        # 1️⃣ Get company profile
        company_doc = get_company_profile(name=company_name)
        if not company_doc:
            return Response({"error": f"Company '{company_name}' not found"}, status=404)

        company_context = {
            "company": company_doc.get("name"),
            "description": company_doc.get("description", ""),
            "competitors": company_doc.get("competitors", []),
        }

        # 2️⃣ Get recent AI articles
        recent_articles = get_recent_articles(limit=limit)
        if not recent_articles:
            return Response({"error": "No recent AI results found"}, status=404)

        # 3️⃣ Run AI idea generator
        logger.info(f"Generating {insight_type} insights for {company_name} ({len(recent_articles)} articles)")
        insights = generate_actionable_insights(company_context, recent_articles, insight_type=insight_type)

        # 4️⃣ Return insights
        return Response({"company": company_name, "count": len(insights), "insights": insights}, status=200)

    except Exception as e:
        logger.exception("ai_generate_ideas error: %s", e)
        return Response({"error": str(e)}, status=500)
    
@api_view(["GET"])
def get_company(request):
    """
    GET /api/company/?name=EcoDrive%20Motors   (optional name)
    Returns the latest (or named) company profile: { name, description, competitors, created_at }.
    """
    name = (request.GET.get("name") or "").strip() or None
    try:
        doc = get_company_profile(name=name)
        if not doc:
            return Response({"error": "company profile not found"}, status=404)
        return Response({
            "id": str(doc.get("_id")),
            "name": doc.get("name"),
            "description": doc.get("description"),
            "competitors": doc.get("competitors", []),
            "created_at": doc.get("created_at"),
        }, status=200)
    except Exception as e:
        logger.exception("get_company error: %s", e)
        return Response({"error": str(e)}, status=500)