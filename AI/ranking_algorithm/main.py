from __future__ import annotations
import argparse
from typing import Dict, Any, List, Tuple
from bson import ObjectId
from pymongo import MongoClient

# --- Mongo Setup ---
MONGO_URI = "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["pace_database"]

# --- Scoring Algorithms ---
from AI.ranking_algorithm.tf_idf_scorer import score_tfidf_simple
from AI.ranking_algorithm.bm25_scorer import BM25Scorer, minmax_normalize
from AI.ranking_algorithm.sbert_scorer import sbert_score_one
from AI.ranking_algorithm.engagement_scorer import engagement_score

# --- Summarization + Topic Detection ---
from AI.Topic_detection.Topic_detection import detect_topic_simple
from AI.Text_summarisation.Text_summariser import generate_summary

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


# -----------------------------------------------------------------------------
# FETCH DOCUMENTS FOR THIS HISTORY
# -----------------------------------------------------------------------------
def fetch_docs(history_id: str):
    history_id = ObjectId(history_id)

    queued = list(db.ai_results.find(
        {"history_id": history_id, "status": "queued"},
        {"url": 1, "raw_id": 1, "source": 1, "published_ts": 1}
    ))

    docs = []
    for q in queued:
        raw = db.raw_insights.find_one({"_id": q["raw_id"]}, {"text": 1, "engagement": 1})
        if raw and raw.get("text"):
            docs.append({
                "_id": q["raw_id"],
                "text": raw["text"],
                "engagement": raw.get("engagement", {}),
                "source": q["source"],
                "published_ts": q["published_ts"],
                "url": q["url"],
            })
    return docs


# -----------------------------------------------------------------------------
# MAIN AI PIPELINE
# -----------------------------------------------------------------------------
def run(history_id: str, keyword: str):
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



    rows = []

    for d in docs:
        per_algo = {}

        # BM25 (already normalized 0..1)
        per_algo["bm25"] = float(bm25_scores.get(d["_id"], 0.0))

        # TF-IDF / SBERT / engagement
        for a in ["tfidf", "sbert", "engagement"]:
            try:
                if a == "sbert":
                    if d["_id"] in top_ids:
                        raw_score = ALGORITHMS["sbert"](keyword, d["text"])
                    else:
                        raw_score = 0.0
                elif a == "tfidf":
                    raw_score = ALGORITHMS["tfidf"](keyword, d["text"])
                elif a == "engagement":
                    raw_score = ALGORITHMS["engagement"](d)
                else:
                    raw_score = 0.0

            except Exception:
                # SBERT model missing, etc.
                raw_score = 0.0

            # Clamp 0..1
            per_algo[a] = max(0.0, min(1.0, float(raw_score)))

        # Weighted linear fusion
        final_score = sum(
            per_algo.get(name, 0.0) * weights.get(name, 0.0)
            for name in use_algos
        )

        rows.append((final_score, d, per_algo))


    rows.sort(key=lambda x: x[0], reverse=True)

    # -----------------------------------------------------------------------------
    # SUMMARIZE + DETECT TOPIC + WRITE RESULTS BACK
    # -----------------------------------------------------------------------------
    items = []
    for rank, (score, d, per_algo) in enumerate(rows, start=1):

        summary = generate_summary(d["text"])  
        topic = detect_topic_simple(d["text"]) 

        items.append({
            "url": d["url"],
            "raw_id": d["_id"],
            "rank": rank,
            "relevance_score": score,
            "per_algo_scores": per_algo,  # <-- new
            "ai_title": topic,
            "ai_summary": summary,
            "tags": [topic],
            "source": d["source"],
            "published_ts": d["published_ts"],
            "status": "done",
        })


    write_ai_results_batch(history_id, items)
    print(f"[SUCCESS] Processed & saved {len(items)} AI-ranked articles.")
    return rows


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AI scoring + summarization pipeline.")
    parser.add_argument("history_id", type=str)
    parser.add_argument("keyword", type=str)
    args = parser.parse_args()

    run(args.history_id, args.keyword)
