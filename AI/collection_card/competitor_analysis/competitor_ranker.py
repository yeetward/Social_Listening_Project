# AI/competitors/competitor_ranker.py
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import re

from .ner_adapter import extract_org_candidates

# Optional SBERT for tiny name-sim boost; safe if not installed
try:
    from sentence_transformers import SentenceTransformer, util
    _SBERT = SentenceTransformer("all-MiniLM-L6-v2")
except Exception:
    _SBERT = None

_COMP_TERMS = {
    "competitor","competitors","rival","rivals","competing","competition",
    "versus","vs","alternative","alternatives","compared to","against","beats","vs."
}
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')
_WORD = re.compile(r"[A-Za-z0-9]+")


def _sentences(text: str) -> List[str]:
    return _SENT_SPLIT.split((text or "").strip())


def _name_variants(name: str) -> List[str]:
    n = (name or "").strip()
    bits = _WORD.findall(n)
    variants = [n]
    if bits:
        variants.append(" ".join(bits))   # strip punctuation
        variants.append(bits[0])          # head token
    # dedupe preserve order
    seen = set()
    out = []
    for v in variants:
        lv = v.lower()
        if v and lv not in seen:
            seen.add(lv)
            out.append(v)
    return out


def _co_mentions(text: str, seed_brand: str, candidate: str) -> Tuple[int, int]:
    """(count both same sentence, count co-mention w/ competitor terms)"""
    both = 0
    both_and_comp = 0
    for s in _sentences(text):
        sl = s.lower()
        b = any(v.lower() in sl for v in _name_variants(seed_brand))
        c = any(v.lower() in sl for v in _name_variants(candidate))
        if b and c:
            both += 1
            if any(t in sl for t in _COMP_TERMS):
                both_and_comp += 1
    return both, both_and_comp


def _domain_hint(candidate: str) -> float:
    tokens = (candidate or "").split()
    if not tokens:
        return 0.0
    if all(tok[:1].isupper() for tok in tokens if tok):
        return 0.1
    return 0.0


def _sbert_name_sim(a: str, b: str) -> float:
    if not _SBERT:
        return 0.0
    emb = _SBERT.encode([a, b], normalize_embeddings=True)
    sim = float(util.cos_sim(emb[0], emb[1]).item())
    return (sim + 1.0) / 2.0  # map [-1..1] -> [0..1]


def _clip01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def rank_competitors_from_articles(
    *,
    company_name: str,
    articles: List[Dict[str, Any]],
    top_n: int = 10,
    min_score: float = 0.25,
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Fusion competitor ranking from the *article batch*:
      1) Extract ORG candidates per article (spaCy or regex)
      2) Score co-mentions vs company + competitor-language proximity
      3) Optional SBERT small name-sim boost

    Returns [{name, score, signals, explanation}]
    """
    # Build one big text block (titles + summaries = compact, high-signal)
    blob_parts: List[str] = []
    for a in articles:
        t = a.get("ai_title", "") or ""
        s = a.get("ai_summary", "") or ""
        blob_parts.append(t)
        blob_parts.append(s)
    big_text = "\n".join(p for p in blob_parts if p)

    if not company_name or not big_text.strip():
        return []

    # 1) candidate orgs
    cands = extract_org_candidates(big_text)

    # 2) dedupe + drop the seed company itself
    seen = set()
    uniq: List[str] = []
    seed_low = company_name.lower().strip()
    for c in cands:
        lc = c.lower().strip()
        if lc and lc != seed_low and lc not in seen:
            seen.add(lc)
            uniq.append(c)

    # Weights
    W = {
        "same_sentence": 0.50,
        "comp_terms":    0.20,
        "domain_hint":   0.05,
        "sbert_name":    0.25,
    }
    if weights:
        W.update(weights)

    # 3) score
    out: List[Dict[str, Any]] = []
    for cand in uniq:
        both, both_comp = _co_mentions(big_text, company_name, cand)
        ss = min(1.0, both / 2.0)      # 0, 0.5, 1.0
        cc = 1.0 if both_comp > 0 else 0.0
        dh = _domain_hint(cand)
        sb = _sbert_name_sim(company_name, cand)

        score = (
            W["same_sentence"] * ss +
            W["comp_terms"]    * cc +
            W["domain_hint"]   * dh +
            W["sbert_name"]    * sb
        )
        score = _clip01(score)

        reasons = []
        if ss >= 1.0: reasons.append(f"frequent co-mention with {company_name}")
        elif ss >= 0.5: reasons.append(f"co-mentioned with {company_name}")
        if cc > 0:    reasons.append("appears near competitor/vs language")
        if dh > 0:    reasons.append("brand-like capitalization")
        if sb >= 0.6: reasons.append("name similarity to peer brands")

        out.append({
            "name": cand,
            "score": round(float(score), 4),
            "signals": {
                "same_sentence": ss,
                "comp_terms": cc,
                "domain_hint": dh,
                "sbert_name": sb
            },
            "explanation": "; ".join(reasons) if reasons else "weak evidence",
        })

    out.sort(key=lambda r: r["score"], reverse=True)
    if min_score is not None:
        out = [r for r in out if r["score"] >= min_score]
    return out[:top_n]
