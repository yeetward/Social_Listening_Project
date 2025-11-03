from __future__ import annotations
import argparse
from typing import Dict, Any, List, Tuple
from bson import ObjectId
from pymongo import MongoClient
import os

# --- Mongo Setup ---
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(MONGO_URI)
db = client["pace_database"]

# --- Scoring Algorithms ---
from AI.ranking_algorithm.tf_idf_scorer import score_tfidf_simple
from AI.ranking_algorithm.bm25_scorer import BM25Scorer, minmax_normalize
from AI.ranking_algorithm.sbert_scorer import sbert_score_one
from AI.ranking_algorithm.engagement_scorer import engagement_score

# --- Summarization + Topic Detection ---
from AI.Topic_detection.Topic_detection import detect_topic_simple
from AI.Text_summarisation.main_summaries import run as generate_summary

# --- Sentiment Analysis ---
from AI.sentiment_analysis.sentiment_analyzer import quick_sentiment

# --- Write Results to ai_results ---
from AI.ranking_algorithm.mongo import write_ai_results_batch

TOPK = 200

ALGORITHMS = {
    "tfidf": lambda keyword, doc: score_tfidf_simple(keyword, doc["text"]),
    "sbert": lambda keyword, doc: sbert_score_one(keyword, doc["text"]),
    "engagement": lambda keyword, doc: engagement_score(doc),
}

DEFAULT_WEIGHTS = {
    "bm25": 0.25,
    "sbert": 0.60,
    "engagement": 0.15,
    "tfidf": 0.05,
}

# ---------------------------------------------------------------------------
# RAW lookups
# ---------------------------------------------------------------------------
RAW_COLLECTIONS = [
    "raw_insights",
    "raw_articles",
    "crawler_pages",
    "content_cache",
    "pages",
    "articles_raw",
]

def _hid_clause(hid: str) -> Dict[str, Any]:
    ors = [{"history_id": hid}]
    try:
        ors.append({"history_id": ObjectId(hid)})
    except Exception:
        pass
    return {"$or": ors}

def _get_raw_doc_by_ref(raw_id, url):
    """Try to fetch a doc with 'text' from any raw-* collection by raw_id then url."""
    proj = {"text": 1, "engagement": 1}
    for coll in RAW_COLLECTIONS:
        if raw_id:
            try:
                doc = db[coll].find_one({"_id": raw_id}, proj)
                if doc and doc.get("text"):
                    return doc
            except Exception:
                pass
        if url:
            doc = db[coll].find_one({"url": url}, proj)
            if doc and doc.get("text"):
                return doc
    return None

def _fallback_ai_text(q):
    """If no raw doc, try to reconstruct text from existing ai_results fields."""
    ai = db.ai_results.find_one({"_id": q["_id"]}, {"ai_summary": 1, "ai_title": 1, "text": 1})
    if not ai:
        return None
    parts = [ai.get("ai_title", ""), ai.get("ai_summary", ""), ai.get("text", "")]
    text = "\n".join(p for p in parts if p).strip()
    return text or None


# ---------------------------------------------------------------------------
# FETCH DOCUMENTS FOR THIS HISTORY
# ---------------------------------------------------------------------------
def fetch_docs(history_id: str) -> List[Dict[str, Any]]:
    # IMPORTANT: include _id in projection (used in fallback)
    queued = list(db.ai_results.find(
        {**_hid_clause(history_id), "status": {"$in": ["queued", "done"]}},
        {"_id": 1, "url": 1, "raw_id": 1, "source": 1, "published_ts": 1}
    ))
    print(f"[INFO] Found {len(queued)} ai_results rows to process for history_id={history_id}")

    docs: List[Dict[str, Any]] = []
    misses_by_raw = 0
    hits = 0

    for q in queued:
        raw_id = q.get("raw_id")
        url    = q.get("url") or ""  # be safe

        raw_doc = _get_raw_doc_by_ref(raw_id, url)

        # if not raw_doc:
        #     # Fallback: if ai_results already has ai_summary/ai_title, use them as text
        #     ai = db.ai_results.find_one({"_id": q["_id"]}, {"ai_summary":1, "ai_title":1})
        #     if ai and (ai.get("ai_summary") or ai.get("ai_title")):
        #         text_fallback = f"{ai.get('ai_title','')}\n{ai.get('ai_summary','')}".strip()
        #         if text_fallback:
        #             hits += 1
        #             docs.append({
        #                 "_id": raw_id or url or q["_id"],   # stable key
        #                 "text": text_fallback,
        #                 "engagement": {},
        #                 "source": q.get("source"),
        #                 "published_ts": q.get("published_ts"),
        #                 "url": url,
        #             })
        #             continue

        #     misses_by_raw += 1
        #     continue
        if not raw_doc:
            text_fallback = _fallback_ai_text(q)
            if text_fallback:
                hits += 1
                docs.append({
                    "_id": raw_id or url or q["_id"],
                    "text": text_fallback,
                    "engagement": {},
                    "source": q.get("source"),
                    "published_ts": q.get("published_ts"),
                    "url": url,
                })
                continue
            misses_by_raw += 1
            continue


        hits += 1
        docs.append({
            "_id": raw_id or url,  # stable key for scoring
            "text": raw_doc.get("text", ""),
            "engagement": raw_doc.get("engagement", {}),
            "source": q.get("source"),
            "published_ts": q.get("published_ts"),
            "url": url,
        })

    print(f"[INFO] Joined {hits} raw docs with text (misses: {misses_by_raw})")
    return docs

# ---------------------------------------------------------------------------
# MAIN AI PIPELINE
# ---------------------------------------------------------------------------
def run(history_id: str, keyword: str):
    # Auto-seed queued rows if none exist
    from AI.ranking_algorithm.seed_ai_results import main as seed_once
    from AI.ranking_algorithm.check_history import clauses as _clauses

    hid_clause = _clauses(history_id)
    if db.ai_results.count_documents({**hid_clause, "status": "queued"}) == 0:
        seed_once(history_id)

    docs = fetch_docs(history_id)
    if not docs:
        print("[INFO] No articles waiting for AI processing.")
        return []
    use_algos = ["tfidf", "bm25", "sbert", "engagement"]
    weights = DEFAULT_WEIGHTS

    # BM25 first-pass
    bm25 = BM25Scorer.from_docs(docs, k1=1.5, b=0.75)
    bm25_raw = bm25.score_all_for_query(keyword)
    bm25_scores = minmax_normalize(bm25_raw)
    top_ids = set(sorted(bm25_scores, key=bm25_scores.get, reverse=True)[:TOPK])

    rows: List[Tuple[float, Dict[str, Any], Dict[str, float]]] = []
    for d in docs:
        per_algo: Dict[str, float] = {}

        # BM25 (already normalized 0..1)
        per_algo["bm25"] = float(bm25_scores.get(d["_id"], 0.0))

        # TF-IDF / SBERT / engagement
        for a in ["tfidf", "sbert", "engagement"]:
            try:
                if a == "sbert":
                    raw_score = ALGORITHMS["sbert"](keyword, d["text"]) if d["_id"] in top_ids else 0.0
                elif a == "tfidf":
                    raw_score = ALGORITHMS["tfidf"](keyword, d["text"])
                elif a == "engagement":
                    raw_score = ALGORITHMS["engagement"](d)
                else:
                    raw_score = 0.0
            except Exception:
                raw_score = 0.0
            per_algo[a] = max(0.0, min(1.0, float(raw_score)))

        final_score = sum(per_algo.get(name, 0.0) * weights.get(name, 0.0) for name in use_algos)
        rows.append((final_score, d, per_algo))

    rows.sort(key=lambda x: x[0], reverse=True)

    # Summarize + Topic + Sentiment + Write back
    items = []
    for rank, (score, d, per_algo) in enumerate(rows, start=1):
        summary = generate_summary(d["text"])
        topic = detect_topic_simple(d["text"])
        sentiment = quick_sentiment(d["text"], method='vader')  # 'positive', 'negative', or 'neutral'
        items.append({
            "url": d["url"],
            "raw_id": d["_id"],
            "rank": rank,
            "relevance_score": score,
            "per_algo_scores": per_algo,
            "ai_title": topic,
            "ai_summary": summary,
            "tags": [topic],
            "sentiment": sentiment,  # <-- Sentiment analysis result
            "source": d["source"],
            "published_ts": d["published_ts"],
            "status": "done",
        })

    write_ai_results_batch(history_id, items)
    print(f"[SUCCESS] Processed & saved {len(items)} AI-ranked articles.")
    return rows
    

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    history_id = "68fdda1caf9de874acb5a32a"  # Example history ID
    keyword = "artificial intelligence"
    run(history_id, keyword)
