# AI/Algorithms/tf_idf_scorer.py
"""
TF-IDF cosine similarity for a single article vs. a keyword.

Usage (from Python):
    from AI.Algorithms.tfidf_scorer import score_one, score_one_doc

    s = score_one("gen ai", body_text, title="Generative AI in 2025", use_bigrams=True)
    # or if you have a Mongo-like dict:
    s = score_one_doc("gen ai", {"title": "Gen AI", "body": "LLMs and RAG..."})
"""

from typing import Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


def score_one(
    keyword: str,
    body: str,
    title: str = "",
    *,
    title_boost: float = 1.15,
    use_bigrams: bool = False,
) -> float:
    """
    Compute TF-IDF cosine similarity between `keyword` and one article (`title` + `body`).

    Returns:
        float in [0, 1]
    Notes:
        - Vectorizer is fit on [keyword, article] only (good for single checks).
        - If `keyword` appears as a substring in `title`, a small boost is applied.
        - Set `use_bigrams=True` to capture phrases (e.g., "gen ai").
    """
    title = (title or "").strip()
    body = (body or "").strip()
    text = (title + "\n" + body).strip()

    # Build a tiny corpus: [query, doc]
    ngram = (1, 2) if use_bigrams else (1, 1)
    vec = TfidfVectorizer(stop_words="english", ngram_range=ngram)
    X = vec.fit_transform([keyword, text])

    # Cosine(query, doc) ∈ [0, 1] for TF-IDF; clip after boost just in case
    sim = float(linear_kernel(X[0:1], X[1:2])[0, 0])

    # Optional title boost
    if title and keyword.lower() in title.lower():
        sim *= title_boost

    # Keep in [0, 1]
    if sim < 0.0:
        sim = 0.0
    elif sim > 1.0:
        sim = 1.0

    return sim


def score_one_doc(keyword: str, doc: Dict) -> float:
    """
    Convenience wrapper for dicts that look like Mongo docs.
    Expects keys: 'body' (required-ish), 'title' (optional).
    """
    return score_one(
        keyword=keyword,
        body=(doc.get("body") or ""),
        title=(doc.get("title") or ""),
    )


__all__ = ["score_one", "score_one_doc"]
