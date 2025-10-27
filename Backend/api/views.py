# Backend/api/views.py
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

import logging, time
from bson import ObjectId
from threading import Thread

from .analytics import trend_timeseries_by_day, trend_top_tags, trend_by_source
from .analytics import global_top_topics

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

# Try to import the AI team's entrypoint
try:
    # expects: def run(history_id: str, keyword: str) -> Any
        from AI.ranking_algorithm.main import run as external_ai_run
except Exception:
    external_ai_run = None
    logger.warning("AI.main.run not importable; will use built-in fallback worker.")

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

# -------------------- Built-in fallback AI worker (your existing summariser) --------------------

# def _process_history_async(history_id: ObjectId, subject: str, batch_size: int = 50):
#     db = get_mongo_db()
#     mark_history_ai_started(history_id)
#     processed = 0

#     try:
#         while True:
#             # Pull a batch of queued items for THIS history only
#             queued = list(
#                 db["ai_results"]
#                 .find({"history_id": ObjectId(history_id), "status": "queued"})
#                 .limit(batch_size)
#             )
#             if not queued:
#                 break

#             # Load raw docs
#             raw_ids = [q.get("raw_id") for q in queued if q.get("raw_id")]
#             raw_map = {
#                 r["_id"]: r
#                 for r in db["raw_insights"].find(
#                     {"_id": {"$in": raw_ids}},
#                     {"title": 1, "text": 1, "published_ts": 1, "source": 1, "url": 1}
#                 )
#             }

#             # Run your AI for this batch (toy logic)
#             items = []
#             for q in queued:
#                 raw = raw_map.get(q.get("raw_id"))
#                 if not raw and q.get("url"):
#                     raw = db["raw_insights"].find_one(
#                         {"url": q["url"]},
#                         {"title": 1, "text": 1, "published_ts": 1, "source": 1, "url": 1}
#                     )
#                 if not raw:
#                     continue

#                 title = raw.get("title") or ""
#                 text  = raw.get("text") or ""

#                 ai_title   = title[:140] or f"{subject} — result"
#                 ai_summary = (text[:700] + "…") if len(text) > 700 else text
#                 relevance  = 1.0

#                 items.append({
#                     "url": q["url"],
#                     "raw_id": q.get("raw_id"),
#                     "source": raw.get("source"),
#                     "published_ts": raw.get("published_ts"),
#                     "rank": None,
#                     "relevance_score": relevance,
#                     "ai_title": ai_title,
#                     "ai_summary": ai_summary,
#                     "status": "done",
#                 })

#             if items:
#                 write_ai_results_batch(history_id, items)
#                 processed += len(items)
#                 mark_history_ai_progress(history_id, processed)

#         mark_history_ai_done(history_id, total_count=processed)

#     except Exception as e:
#         logger.exception("AI worker failed for history=%s: %s", history_id, e)
#         # You could mark as failed here if you add such a field

def _process_history_async(history_id: ObjectId, subject: str, batch_size: int = 50):
    db = get_mongo_db()  # so we can fallback-count if needed
    mark_history_ai_started(history_id)
    try:
        rows = external_ai_run(str(history_id), subject)  # subject is the keyword
        total = len(rows) if rows is not None else db["ai_results"].count_documents(
            {"history_id": ObjectId(history_id), "status": "done"}
        )
        mark_history_ai_done(history_id, total_count=total)
    except Exception as e:
        logger.exception("AI worker failed for history=%s: %s", history_id, e)
        # (optional) set a failure flag on the history doc here


# -------------------- External AI kicker (prefers AI.main.run) --------------------

def _kick_external_ai(history_id: ObjectId, subject: str):
    """
    Fire the AI team's pipeline in-process without blocking the request.
    If AI module isn't importable or raises, fall back to the built-in worker.
    """
    db = get_mongo_db()
    try:
        mark_history_ai_started(history_id)

        if not external_ai_run:
            logger.warning("AI.main.run unavailable; using fallback worker.")
            _process_history_async(history_id, subject)
            return

        # Call the AI team's function (we're already on a background thread)
        external_ai_run(str(history_id), subject)

        # After it returns, count produced 'done' results
        total = db["ai_results"].count_documents({"history_id": ObjectId(history_id), "status": "done"})
        mark_history_ai_progress(history_id, total)
        mark_history_ai_done(history_id, total_count=total)
        logger.info("External AI finished for history=%s, produced=%s items.", history_id, total)

    except Exception as e:
        logger.exception("External AI run failed; falling back. %s", e)
        _process_history_async(history_id, subject)

# -------------------- Search + ingest --------------------

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

@api_view(["GET"])
def get_company(request):
    """
    GET /api/company/?name=EcoDrive%20Motors   (optional name)
    Returns the latest (or named) company profile: { name, description, created_at }.
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