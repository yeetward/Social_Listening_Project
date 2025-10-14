# AI/Algorithms/bm25_scorer.py
from __future__ import annotations
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import re

_word = re.compile(r"[A-Za-z0-9]+")

def _tok(s: str) -> List[str]:
    if not s:
        return []
    return _word.findall(s.lower())

class BM25Scorer:
    """
    Fit once on the current batch of docs, then score a query against all docs.
    Keep an index: doc_id -> position, so we can fetch per-doc scores quickly.
    """
    def __init__(self, bm25: BM25Okapi, id_at_idx: List[Any], idx_of_id: Dict[Any, int]):
        self._bm25 = bm25
        self._id_at_idx = id_at_idx
        self._idx_of_id = idx_of_id

    @classmethod
    def from_docs(cls, docs: List[Dict[str, Any]]) -> "BM25Scorer":
        """
        Build a BM25 index over docs (title + body).
        """
        id_at_idx: List[Any] = []
        corpus_tokens: List[List[str]] = []

        for d in docs:
            did = d.get("_id")
            title = (d.get("title") or "").strip()
            body = (d.get("body") or "").strip()
            text = f"{title}\n{body}".strip()
            tokens = _tok(text)
            id_at_idx.append(did)
            corpus_tokens.append(tokens)

        bm25 = BM25Okapi(corpus_tokens)
        idx_of_id = {did: i for i, did in enumerate(id_at_idx)}
        return cls(bm25=bm25, id_at_idx=id_at_idx, idx_of_id=idx_of_id)

    def score_all_for_query(self, query: str) -> Dict[Any, float]:
        """
        Return a dict {doc_id: bm25_score} for the given query across the whole corpus.
        """
        qtok = _tok(query or "")
        if not qtok:
            return {did: 0.0 for did in self._id_at_idx}
        scores = self._bm25.get_scores(qtok)  # numpy array aligned to id_at_idx
        return {did: float(scores[i]) for i, did in enumerate(self._id_at_idx)}
