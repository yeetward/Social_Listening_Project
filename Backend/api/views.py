from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

import logging, time
from bson import ObjectId
from .analytics import trend_timeseries_by_day, trend_top_tags, trend_by_source
from .analytics import global_top_topics

from threading import Thread
from .persist import (
    get_mongo_db,
    mark_history_ai_started,
    mark_history_ai_progress,
    mark_history_ai_done,
    write_ai_results_batch,
)

from .sources import REGISTRY as FETCHERS
from .persist import (
    get_mongo_db,
    create_history,
    persist_raw_insights,
    seed_ai_result_stubs,      # NEW
)

logger = logging.getLogger(__name__)

def health(request):
    return JsonResponse({"status": "ok", "version": "v1"})

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

# for clling the ai based on the history id
def _process_history_async(history_id: ObjectId, subject: str, batch_size: int = 50):
    db = get_mongo_db()
    mark_history_ai_started(history_id)
    processed = 0

    try:
        while True:
            # Pull a batch of queued items for THIS history only
            queued = list(
                db["ai_results"]
                .find({"history_id": ObjectId(history_id), "status": "queued"})
                .limit(batch_size)
            )
            if not queued:
                break

            # Load raw docs
            raw_ids = [q.get("raw_id") for q in queued if q.get("raw_id")]
            raw_map = {
                r["_id"]: r
                for r in db["raw_insights"].find(
                    {"_id": {"$in": raw_ids}},
                    {"title": 1, "text": 1, "published_ts": 1, "source": 1, "url": 1}
                )
            }

            # Run your AI for this batch
            items = []
            for q in queued:
                raw = raw_map.get(q.get("raw_id"))
                if not raw:
                    # fallback by URL if needed
                    if q.get("url"):
                        raw = db["raw_insights"].find_one(
                            {"url": q["url"]},
                            {"title": 1, "text": 1, "published_ts": 1, "source": 1, "url": 1}
                        )
                if not raw:
                    continue

                # --- Replace the following with your real AI calls ---
                title = raw.get("title") or ""
                text  = raw.get("text") or ""

                # Example toy logic; plug in Pace_Unit/AI/main.py funcs instead
                ai_title   = title[:140] or f"{subject} — result"
                ai_summary = (text[:700] + "…") if len(text) > 700 else text
                relevance  = 1.0  # compute using your bm25/sbert/etc.
                # -----------------------------------------------

                items.append({
                    "url": q["url"],
                    "raw_id": q.get("raw_id"),
                    "source": raw.get("source"),
                    "published_ts": raw.get("published_ts"),
                    "rank": None,  # or compute a rank later
                    "relevance_score": relevance,
                    "ai_title": ai_title,
                    "ai_summary": ai_summary,
                    # if you added a single 'summary' field too:
                    # "summary": ai_summary,
                    "status": "done",
                })

            if items:
                write_ai_results_batch(history_id, items)
                processed += len(items)
                mark_history_ai_progress(history_id, processed)

        mark_history_ai_done(history_id, total_count=processed)

    except Exception as e:
        logger.exception("AI worker failed for history=%s: %s", history_id, e)
        # (optional) you could mark the history as failed here


@api_view(["POST"])
def search_posts(request):
    """
    Pipeline:
      - Create a history record.
      - For each selected source, fetch (default 120).
      - Interleave, dedupe by URL, apply freshness window.
      - Persist up to persist_pool_limit into raw_insights (global cache).
      - Seed ai_results stubs (status='queued') for this history_id.
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

    # NEW: seed per-run ai_results stubs so the AI knows what to process
    seeded = seed_ai_result_stubs(history_id, to_persist)

    Thread(
        target=_process_history_async,
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
            "seeded_ai_results": seeded,   # NEW: number of stubs created
        }
    }, status=200)
    resp["X-Sources-Used"] = ",".join(selected)
    resp["X-Fetch-Limit"] = str(fetch_limit)
    resp["X-Persist-Pool-Limit"] = str(persist_pool_limit)
    resp["X-Freshness-Days"] = str(days)
    return resp

# -------------------- NEW READ ENDPOINTS --------------------

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
        oid = ObjectId(hid)  # convert ONCE here
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
        # allow optional status filter; default to 'done'
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

# -------------------- Debug --------------------

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
    
# Backend/api/views.py


# from django.http import JsonResponse
# from rest_framework.decorators import api_view
# from rest_framework import status
# from rest_framework.response import Response

# from .models import FetchLog
# from .sources import REGISTRY as FETCHERS
# from .persist import (
#     create_history,
#     upsert_raw_insights_many,
#     update_history_counts,
# )

# import logging
# import time

# logger = logging.getLogger(_name_)

# def health(request):
#     return JsonResponse({"status": "ok", "version": "v2"})

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

# @api_view(["POST"])
# def search_posts(request):
#     """
#     Start a search job:
#       1) Build query from subject + optional location/industry
#       2) Fetch from selected/all sources
#       3) Interleave + dedupe + freshness filter + relevance
#       4) Persist up to persist_pool_limit rows into raw_insights
#       5) Create a history record and return its id + counts

#     Response:
#       {
#         "history_id": "...",
#         "subject": "...",
#         "raw_persisted": 500,
#         "sources_used": [...],
#         "ai_ready": false,
#         "ai_target": 100
#       }
#     """
#     data = request.data or {}
#     subject  = (data.get("subject")  or "").strip()
#     location = (data.get("location") or "").strip()
#     industry = (data.get("industry") or "").strip()

#     if not subject:
#         return Response({"error": "subject is required"}, status=status.HTTP_400_BAD_REQUEST)

#     # ---- limits ----
#     # bigger defaults per sponsor
#     try:
#         fetch_limit = int(data.get("fetch_limit") or 120)  # per-source
#     except Exception:
#         fetch_limit = 120
#     fetch_limit = max(10, min(fetch_limit, 300))

#     # total we aim to persist to raw_insights
#     try:
#         persist_pool_limit = int(data.get("persist_pool_limit") or 500)
#     except Exception:
#         persist_pool_limit = 500
#     persist_pool_limit = max(50, min(persist_pool_limit, 1000))

#     try:
#         days = int(data.get("days") or 7)
#     except Exception:
#         days = 7

#     # choose sources
#     selected = _parse_sources_param(data.get("sources") or data.get("source"))
#     if not selected:
#         selected = list(FETCHERS.keys())

#     # upstream query string
#     query_terms = [subject]
#     if location: query_terms.append(location)
#     if industry: query_terms.append(industry)
#     upstream_query = " ".join(query_terms)

#     # fetch
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

#     # interleave
#     interleaved = []
#     max_len = max((len(lst) for lst in sources_data), default=0)
#     for i in range(max_len):
#         for lst in sources_data:
#             if i < len(lst):
#                 interleaved.append(lst[i])

#     # dedupe by URL
#     seen = set()
#     deduped = []
#     for p in interleaved:
#         u = p.get("url")
#         if not u or u in seen:
#             continue
#         seen.add(u)
#         deduped.append(p)

#     # freshness
#     now = int(time.time())
#     cutoff = now - days * 86400
#     fresh = [p for p in deduped if (p.get("published_ts") or 0) >= cutoff] or deduped

#     # relevance
#     subj_l = subject.lower()
#     loc_l  = location.lower()
#     ind_l  = industry.lower()

#     def relevance(p):
#         title = (p.get("title") or "").lower()
#         body  = (p.get("text")  or "").lower()
#         hay   = f"{title} {body}"
#         if subj_l and subj_l not in hay:
#             return None
#         score = 0
#         if subj_l in title:
#             score += 3
#         elif subj_l in body:
#             score += 1
#         if loc_l and loc_l in hay:
#             score += 2
#         if ind_l and ind_l in hay:
#             score += 2
#         return score

#     scored = []
#     for p in fresh:
#         s = relevance(p)
#         if s is not None:
#             scored.append((s, p.get("published_ts") or 0, p))

#     if not scored:
#         logger.info("/api/search subject='%s' -> 0 posts (sources=%s)", subject, ",".join(selected))
#         # still create a history so FE has something to show in history list
#         history_id = create_history(
#             subject,
#             location=location,
#             industry=industry,
#             sources_used=selected,
#             params={"days": days, "fetch_limit": fetch_limit, "persist_pool_limit": persist_pool_limit},
#             ai_target=100,
#         )
#         # after creating history_id
#         created, updated = upsert_raw_insights_many(ranked, cap=persist_pool_limit, history_id=history_id)

#         update_history_counts(history_id, raw_count=0, ai_ready=False, ai_count=0)
#         return Response({
#             "history_id": history_id,
#             "subject": subject,
#             "raw_persisted": 0,
#             "sources_used": selected,
#             "ai_ready": False,
#             "ai_target": 100,
#         }, status=200)

#     # rank by (score desc, recency desc)
#     scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
#     ranked = [p for (_s, _ts, p) in scored]

#     # create history first
#     history_id = create_history(
#         subject,
#         location=location,
#         industry=industry,
#         sources_used=selected,
#         params={"days": days, "fetch_limit": fetch_limit, "persist_pool_limit": persist_pool_limit},
#         ai_target=100,
#     )

#     # persist up to cap into raw_insights
#     created, updated = upsert_raw_insights_many(ranked, cap=persist_pool_limit)
#     raw_persisted = created + updated
#     update_history_counts(history_id, raw_count=raw_persisted, ai_ready=False, ai_count=0)

#     logger.info(
#         "/api/search subject='%s' -> persisted=%d (created=%d updated=%d) fetch_limit=%d sources=%s",
#         subject, raw_persisted, created, updated, fetch_limit, ",".join(selected)
#     )

#     # also store a small fetch log in SQLite (optional; keeping your existing pattern)
#     try:
#         FetchLog.objects.create(
#             subject=subject,
#             location=location,
#             industry=industry,
#             days=days,
#             limit=min(10, raw_persisted),  # display cap no longer used, keep a value
#             result_count=raw_persisted,
#             search_params={"fetch_limit": fetch_limit, "persist_pool_limit": persist_pool_limit},
#         )
#     except Exception as e:
#         logger.exception("fetchlog error: %s", e)

#     # return a compact job summary (FE will later call /api/results?history_id=...)
#     resp = Response({
#         "history_id": history_id,
#         "subject": subject,
#         "raw_persisted": raw_persisted,
#         "sources_used": selected,
#         "ai_ready": False,
#         "ai_target": 100
#     }, status=200)

#     # debug headers
#     resp["X-Fetch-Limit"] = str(fetch_limit)
#     resp["X-Persist-Cap"] = str(persist_pool_limit)
#     resp["X-Freshness-Days"] = str(days)
#     resp["X-Sources-Used"] = ",".join(selected)
#     resp["X-Source-Counts"] = ";".join(f"{k}={per_source_counts.get(k,0)}" for k in selected)
#     return resp

# @api_view(["GET"])
# def mongo_status(request):
#     try:
#         from .persist import get_mongo_db
#         db = get_mongo_db()
#         names = sorted(db.list_collection_names())
#         counts = {}
#         for c in ["raw_insights", "ai_results", "history"]:
#             if c in names:
#                 counts[c] = db[c].count_documents({})
#         return Response({"db": db.name, "collections": names, "counts": counts}, status=200)
#     except Exception as e:
#         return Response({"error": str(e)}, status=500)
    

# # --------------------------------------------------------------------------
# # New read endpoints for FE & AI integration
# # --------------------------------------------------------------------------

# from bson import ObjectId
# from .persist import get_mongo_db

# @api_view(["GET"])
# def list_history(request):
#     """
#     List recent search history entries.
#     Optional query params:
#       - limit (default 10)
#       - ai_only=true (to show only processed)
#     """
#     try:
#         db = get_mongo_db()
#         limit = int(request.GET.get("limit", 10))
#         ai_only = request.GET.get("ai_only", "").lower() in ("1", "true", "yes")

#         coll = db["history"]
#         query = {}
#         if ai_only:
#             query["ai_ready"] = True

#         docs = list(
#             coll.find(query)
#             .sort("created_at", -1)
#             .limit(limit)
#         )

#         # clean ObjectIds for JSON
#         for d in docs:
#             d["_id"] = str(d["_id"])
#             d.pop("_class", None)

#         return Response(docs, status=200)
#     except Exception as e:
#         return Response({"error": str(e)}, status=500)


# @api_view(["GET"])
# def list_ai_results(request):
#     """
#     Get AI-processed results for a given history_id.

#     Query params:
#       - history_id (required)
#       - page (default 1)
#       - page_size (default 10)
#     """
#     history_id = request.GET.get("history_id")
#     if not history_id:
#         return Response({"error": "history_id is required"}, status=400)

#     try:
#         page = int(request.GET.get("page", 1))
#         page_size = int(request.GET.get("page_size", 10))
#         skip = (page - 1) * page_size

#         db = get_mongo_db()
#         coll = db["ai_results"]

#         q = {"history_id": ObjectId(history_id)}
#         total = coll.count_documents(q)
#         cursor = (
#             coll.find(q)
#             .sort("rank", 1)
#             .skip(skip)
#             .limit(page_size)
#         )

#         docs = list(cursor)
#         for d in docs:
#             d["_id"] = str(d["_id"])
#             if "history_id" in d and isinstance(d["history_id"], ObjectId):
#                 d["history_id"] = str(d["history_id"])

#         return Response(
#             {
#                 "history_id": history_id,
#                 "page": page,
#                 "page_size": page_size,
#                 "total": total,
#                 "results": docs,
#             },
#             status=200,
#         )
#     except Exception as e:
#         return Response({"error": str(e)}, status=500)