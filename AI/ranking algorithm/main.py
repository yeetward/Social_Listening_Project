# AI/main.py

# The plan is to iterate over every article. For each article, it gets processed through every algorithm and gets a score. 
# Algorithms to use:
# TF-IDF
# SBERT
# Engagement Metrics

# Toggler for LLM?
# After Algorithms, the score gets plugged into a neural network to get a final score. The articles have a score. 
# Then a simple sorting algorithm is used to sort the articles by score.

# main.py  (project root)
from __future__ import annotations
from typing import Dict, Any, Callable, List, Tuple
import argparse
import json

# Mongo + algorithms
from AI.Mongo.mongo_client import get_db
from AI.Mongo.save_scores import upsert_scores
from AI.Algorithms.tf_idf_scorer import score_tfidf_simple
from AI.Algorithms.bm25_scorer import BM25Scorer, minmax_normalize
from AI.Algorithms.sbert_scorer import sbert_score_one
from AI.Algorithms.engagement_scorer import engagement_score
from AI.Algorithms.combiner import weighted_combine
from AI.config import Weights

TOPK = 200  # rerank budget

# Algorithm registry 
AlgorithmFn = Callable[[str, Dict[str, Any]], float]

ALGORITHMS: Dict[str, AlgorithmFn] = {
    # "tfidf": lambda keyword, doc: score_one_doc(keyword, doc), 
    "tfidf": lambda keyword, doc: score_tfidf_simple(keyword, doc),  # optional
    
    # "sbert": lambda keyword, doc: sbert_score_one(keyword, doc),   
    "sbert": lambda keyword, doc: sbert_score_one(keyword, doc),
    
    # "engagement": lambda keyword, doc: engagement_score(doc),     
    "engagement": lambda keyword, doc: engagement_score(doc)

    # TODO: LLM? (ask sponsor)
}

# sensible defaults (tune with sponsor)
# Fusion defaults: SBERT > BM25 > Engagement; TF-IDF very small if enabled
DEFAULT_WEIGHTS: Dict[str, float] = {
    "bm25": 0.25,
    "sbert": 0.60,
    "engagement": 0.15,
    "tfidf": 0.05,
}


# Data access - fetch articles from Mongo
def fetch_docs(limit: int = 0) -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db["posts"].find({}, {"_id": 1, "title": 1, "body": 1, "engagement": 1})
    if limit > 0:
        cursor = cursor.limit(limit)
    return list(cursor)

def _minmax(scores: Dict[Any, float]) -> Dict[Any, float]:
    """Normalize scores between 0–1 for easier fusion with other algorithms."""
    if not scores:
        return {}
    vals = list(scores.values())
    vmin, vmax = min(vals), max(vals)
    rng = (vmax - vmin) or 1.0
    return {k: (v - vmin) / rng for k, v in scores.items()}


# runner
def run(keyword: str, *, limit: int = 0, algos: List[str] | None = None, weights: Dict[str, float] | None = None, persist: bool = True,) -> List[Tuple[float, Dict[str, Any], Dict[str, float]]]:
    docs = fetch_docs(limit)
    if not docs:
        print("No documents found in 'posts'.")
        return []
    
    # Default: lexical(BM25) + semantic(SBERT) + tie-break(Engagement)
    use_algos = algos if algos else ["bm25", "sbert", "engagement"]

    # Check algo names
    for a in use_algos:
        if a != "bm25" and a not in ALGORITHMS:
            raise ValueError(f"Unknown algorithm '{a}'. Available: bm25 + {list(ALGORITHMS)}")

    # Weights
    use_weights = weights or {k: DEFAULT_WEIGHTS.get(k, 0.0) for k in use_algos}

   
    bm25_scores: Dict[Any, float] = {}
    if "bm25" in use_algos:
        bm25 = BM25Scorer.from_docs(docs, k1=1.5, b=0.75)
        bm25_scores = bm25.score_all_for_query(keyword)
        bm25_scores = _minmax(bm25_scores)

    rows: List[Tuple[float, Dict[str, Any], Dict[str, float]]] = []

    # after bm25_scores normalization
    if "bm25" in use_algos:
        top_ids = set(sorted(bm25_scores, key=bm25_scores.get, reverse=True)[:TOPK])
    else:
        # No BM25 selected: SBERT should score ALL docs
        top_ids = {d["_id"] for d in docs}



    for d in docs:
        per_algo: Dict[str, float] = {}

        # BM25 from precomputed batch
        if "bm25" in use_algos:
            per_algo["bm25"] = float(bm25_scores.get(d["_id"], 0.0))

        # The rest from the registry
        for a in use_algos:
            if a == "bm25":
                continue
            try:
                if a == "sbert":
                    score = float(ALGORITHMS[a](keyword, d)) if d["_id"] in top_ids else 0.0
                else:
                    score = float(ALGORITHMS[a](keyword, d))
                # Optional: clamp non-BM25 to [0,1] for stable fusion
                if a != "bm25":
                    score = max(0.0, min(1.0, score))
                per_algo[a] = score
            except Exception:
                per_algo[a] = 0.0  # fail-safe per-algo



        # Weighted fusion (manual weights for MVP)
        final_score = sum(per_algo.get(a, 0.0) * use_weights.get(a, 0.0) for a in use_algos)
        rows.append((final_score, d, per_algo))

        if persist:
            try:
                upsert_scores(d["_id"], keyword, final_score, per_algo)
            except Exception as e:
                print(f"[WARN] upsert failed for id={d.get('_id')}: {e}")

    rows.sort(key=lambda t: t[0], reverse=True)
    return rows
    
    

# # default algo to use is sbert
#     use_algos = algos if algos else ["sbert"]

# # Checking if all the algos are valid (can remove this depending on the approach. Maybe a toggle button? or just have all of them)
#     for a in use_algos:
#         if a not in ALGORITHMS:
#             raise ValueError(f"Unknown algorithm '{a}'. Available: {list(ALGORITHMS)}")

#     use_weights = weights or {k: DEFAULT_WEIGHTS.get(k, 0.0) for k in use_algos}
    
#     rows: List[Tuple[float, Dict[str, Any], Dict[str, float]]] = []

#     for d in docs:
#         per_algo: Dict[str, float] = {}
#         for a in use_algos:
#             try:
#                 per_algo[a] = float(ALGORITHMS[a](keyword, d))
#             except Exception:
#                 per_algo[a] = 0.0  # fail-safe per-algo
        
#         # TODO: Need to have a NN to combine the scores
#         # simple combiner for now: mean of selected algos
#         final_score = sum(per_algo.get(a, 0.0) * use_weights.get(a, 0.0) for a in use_algos)
#         rows.append((final_score, d, per_algo))

#         if persist:
#             try:
#                 upsert_scores(d["_id"], keyword, final_score, per_algo)
#             except Exception as e:
#                 print(f"[WARN] upsert failed for id={d.get('_id')}: {e}")

#     rows.sort(key=lambda t: t[0], reverse=True)
#     return rows

# ---- CLI ----
# if __name__ == "__main__":
#     p = argparse.ArgumentParser(description="Score and rank Mongo posts by keyword.")
#     p.add_argument("keyword", type=str, help="Query keyword")
#     p.add_argument("--limit", type=int, default=200, help="Max docs to score (0 = all)")
#     p.add_argument("--algos", nargs="+", default=["sbert", "tfidf", "engagement"], help="Algorithms to run")
#     p.add_argument("--weights", type=str, default="", help='JSON dict, e.g. {"tfidf":0.35,"sbert":0.45,"engagement":0.20}')
#     p.add_argument("--no-persist", action="store_true", help="Do not write scores back to Mongo")
#     args = p.parse_args()

#     w = None
#     if args.weights:
#         try:
#             w = json.loads(args.weights)
#         except Exception as e:
#             p.error(f"Invalid --weights JSON: {e}")

#     rows = run(
#         args.keyword,
#         limit=args.limit,
#         algos=args.algos,
#         weights=w,
#         persist=not args.no_persist,
#     )
#     rows = rows or []
#     print(json.dumps({"processed": len(rows), "top_score": rows[0][0] if rows else None}))

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Score and rank Mongo posts by keyword.")
    p.add_argument("keyword", type=str, help="Query keyword")
    p.add_argument("--limit", type=int, default=200, help="Max docs to score (0 = all)")
    p.add_argument(
        "--algos",
        nargs="+",
        default=["bm25", "sbert", "engagement"],   # BM25 primary; TF-IDF optional
        help="Algorithms to run (e.g., bm25 sbert engagement [tfidf])",
    )
    p.add_argument(
        "--weights",
        type=str,
        default="",
        help='JSON dict, e.g. {"bm25":0.25,"sbert":0.60,"engagement":0.15,"tfidf":0.05}',
    )
    p.add_argument("--no-persist", action="store_true", help="Do not write scores back to Mongo")
    args = p.parse_args()

    w = None
    if args.weights:
        try:
            w = json.loads(args.weights)
        except Exception as e:
            p.error(f"Invalid --weights JSON: {e}")

    rows = run(
        args.keyword,
        limit=args.limit,
        algos=args.algos,
        weights=w,
        persist=not args.no_persist,
    )
    rows = rows or []
    print(json.dumps({"processed": len(rows), "top_score": rows[0][0] if rows else None}))