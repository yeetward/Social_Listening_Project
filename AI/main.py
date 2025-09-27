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

# Mongo + algorithms
from AI.Mongo.mongo_client import get_db
from AI.Algorithms.tf_idf_scorer import score_one_doc

# ---- Algorithm registry (add more later) ----
AlgorithmFn = Callable[[str, Dict[str, Any]], float]

ALGORITHMS: Dict[str, AlgorithmFn] = {
    "tfidf": lambda keyword, doc: score_one_doc(keyword, doc),
    # "sbert": lambda keyword, doc: sbert_score_one(keyword, doc),   # TODO
    # "engagement": lambda keyword, doc: engagement_score(doc),      # TODO
}

# ---- Data access ----
def fetch_docs(limit: int = 0) -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db["posts"].find({}, {"_id": 1, "title": 1, "body": 1, "engagement": 1})
    if limit > 0:
        cursor = cursor.limit(limit)
    return list(cursor)

# ---- Runner ----
def run(keyword: str, *, limit: int = 0, algos: List[str] | None = None) -> List[Tuple[float, Dict[str, Any], Dict[str, float]]]:
    docs = fetch_docs(limit)
    if not docs:
        print("No documents found in 'posts'.")
        return []

    use_algos = algos if algos else ["tfidf"]
    for a in use_algos:
        if a not in ALGORITHMS:
            raise ValueError(f"Unknown algorithm '{a}'. Available: {list(ALGORITHMS)}")

    rows: List[Tuple[float, Dict[str, Any], Dict[str, float]]] = []
    for d in docs:
        per_algo: Dict[str, float] = {}
        for a in use_algos:
            try:
                per_algo[a] = float(ALGORITHMS[a](keyword, d))
            except Exception:
                per_algo[a] = 0.0  # fail-safe per-algo
        # simple combiner for now: mean of selected algos
        final_score = sum(per_algo.values()) / len(use_algos) if use_algos else 0.0
        rows.append((final_score, d, per_algo))

    rows.sort(key=lambda t: t[0], reverse=True)

    # pretty print
    print(f"\nKeyword: {keyword} | docs={len(docs)} | algos={','.join(use_algos)}")
    print("-" * 100)
    for i, (final_score, d, per_algo) in enumerate(rows, 1):
        title = (d.get('title') or '').strip()
        short = (title[:80] + "…") if len(title) > 81 else title
        print(f"{i:>3}. final={final_score:>8.6f}  id={d['_id']}  title={short}  {per_algo}")
    print("-" * 100)
    print("Note: per-article TF-IDF refits its vectorizer each time; scores are good per doc, "
          "but not strictly comparable across docs. For consistent ranking across many docs, "
          "switch to a batch TF-IDF later.")

    return rows

# ---- CLI ----
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("keyword", type=str)
    p.add_argument("--limit", type=int, default=0, help="limit N docs (0 = all)")
    p.add_argument("--algos", nargs="+", default=["tfidf"], help="algos to run, e.g. --algos tfidf")
    args = p.parse_args()
    run(args.keyword, limit=args.limit, algos=args.algos)
