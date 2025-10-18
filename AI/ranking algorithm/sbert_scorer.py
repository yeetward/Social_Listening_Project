# AI/Algorithms/sbert_scorer.py
"""
SBERT cosine similarity for a single article vs. a keyword.

"""

from typing import Dict
from sentence_transformers import SentenceTransformer, util

_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def sbert_score_one(keyword: str, doc: Dict) -> float:
    """
    returns a semantic similarity score in [0, 1]
    """
    title = (doc.get("title") or "").strip()
    body = (doc.get("body") or "").strip()
    text = f"{title}\n{body}".strip()
    if not text or not keyword:
        return 0.0

    m = _get_model()
    q_emb = m.encode(keyword, normalize_embeddings=True)
    d_emb = m.encode(text, normalize_embeddings=True)
    sim = float(util.cos_sim(q_emb, d_emb).item())  # [-1, 1]
    # map to [0, 1]
    return max(0.0, min((sim + 1.0) / 2.0, 1.0))

