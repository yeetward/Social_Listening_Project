# AI/Algorithms/tf_idf_scorer.py
from typing import Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# Module defaults (tune centrally)
TITLE_BOOST_DEFAULT = 1.15
USE_BIGRAMS_DEFAULT = False

def _clean_text(x) -> str:
    if x is None:
        return ""
    if not isinstance(x, str):
        x = str(x)
    return x.strip()

def _tfidf_pair_cosine(query: str, text: str, use_bigrams: bool = False) -> float:
    query = _clean_text(query)
    text  = _clean_text(text)
    if not query or not text:
        return 0.0
    ngram = (1, 2) if use_bigrams else (1, 1)
    X = TfidfVectorizer(stop_words="english", ngram_range=ngram).fit_transform([query, text])
    sim = float(linear_kernel(X[0:1], X[1:2])[0, 0])
    return max(0.0, min(1.0, sim))  # clip to [0,1]

def _score_simple_core(keyword: str, title: str, body: str, *, title_boost: float, use_bigrams: bool) -> float:
    s_title = _tfidf_pair_cosine(keyword, title, use_bigrams)
    s_body  = _tfidf_pair_cosine(keyword, body,  use_bigrams)
    return max(0.0, min(1.0, title_boost * s_title + s_body))

def score_tfidf_simple(keyword: str, doc: Dict[str, Any]) -> float:
    title = _clean_text(doc.get("title"))
    body  = _clean_text(doc.get("body"))

    return _score_simple_core(
        keyword, title, body,
        title_boost=TITLE_BOOST_DEFAULT,
        use_bigrams=USE_BIGRAMS_DEFAULT,
    )

__all__ = ["score_tfidf_simple"]

