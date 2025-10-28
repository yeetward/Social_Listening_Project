# AI/ML/competitor_fusion.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional
import math
import re


from AI.ML.ner_adapter import extract_org_candidates

# --- Optional SBERT name-sim boost (safe if not installed) ---
try:
    from sentence_transformers import SentenceTransformer, util
    _SBERT = SentenceTransformer("all-MiniLM-L6-v2")
except Exception:
    _SBERT = None

_COMP_TERMS = {
    "competitor","competitors","rival","rivals","competing","competition",
    "versus","vs","alternative","alternatives","compared to","against"
}
_WORD = re.compile(r"[A-Za-z0-9]+")

def _sentences(text: str) -> List[str]:
    # Simple splitter; good enough for MVP (you can swap for nltk later)
    return re.split(r'(?<=[.!?])\s+', text.strip())

def _contains_term(s: str, terms: set[str]) -> bool:
    s_low = s.lower()
    return any(t in s_low for t in terms)

def _contains_any(s: str, bag: List[str]) -> bool:
    s_low = s.lower()
    return any(x.lower() in s_low for x in bag if x)

def _name_variants(name: str) -> List[str]:
    # Generate simple brand variants (Apple Inc. -> Apple, Apple Inc)
    n = (name or "").strip()
    bits = _WORD.findall(n)
    variants = [n]
    if bits:
        variants.append(" ".join(bits))
        variants.append(bits[0])
    return list(dict.fromkeys(variants))  # unique, keep order

def _brand_near_competitor_terms(sent: str, seed_brand: str, candidate: str) -> float:
    """
    Score if seed brand, candidate and competitor terms co-occur in the same sentence.
    """
    s = sent.lower()
    b_hit = any(v.lower() in s for v in _name_variants(seed_brand))
    c_hit = any(v.lower() in s for v in _name_variants(candidate))
    comp = _contains_term(s, _COMP_TERMS)
    return 1.0 if (b_hit and c_hit and comp) else 0.0

def _same_sentence_hits(text: str, seed_brand: str, candidate: str) -> Tuple[int, int]:
    """
    Count sentences that include both names (with/without explicit competitor terms).
    """
    both = 0
    both_and_comp = 0
    for sent in _sentences(text):
        s = sent.lower()
        b_hit = any(v.lower() in s for v in _name_variants(seed_brand))
        c_hit = any(v.lower() in s for v in _name_variants(candidate))
        if b_hit and c_hit:
            both += 1
            if _contains_term(s, _COMP_TERMS):
                both_and_comp += 1
    return both, both_and_comp

def _industry_location_boost(text: str, *, industry: Optional[List[str]], location: Optional[List[str]]) -> float:
    """
    Lightweight boost if article contains industry/location hints.
    """
    score = 0.0
    if industry:
        score += 0.15 if _contains_any(text, industry) else 0.0
    if location:
        score += 0.10 if _contains_any(text, location) else 0.0
    return min(0.25, score)

def _domain_hint(candidate: str) -> float:
    """
    If the candidate looks like a brand (single capitalized token or proper-case), tiny boost.
    """
    cand = candidate.strip()
    if not cand:
        return 0.0
    # Heuristic: Title Case single/multi-word brand-ish names
    tokens = cand.split()
    if all(t[:1].isupper() for t in tokens if t):
        return 0.1
    return 0.0

def _sbert_name_sim(seed_brand: str, candidate: str) -> float:
    """
    Optional tiny boost for name-kind similarity (company vs company) using SBERT.
    NOT semantic of the full article; just name sim to avoid false positives.
    """
    if not _SBERT:
        return 0.0
    emb = _SBERT.encode([seed_brand, candidate], normalize_embeddings=True)
    sim = float(util.cos_sim(emb[0], emb[1]).item())
    # Map [-1..1] to [0..1]
    return (sim + 1.0) / 2.0

def _clip01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def rank_competitors_fused(
    *,
    text: str,
    seed_brand: str,
    industry: Optional[List[str]] = None,
    location: Optional[List[str]] = None,
    extra_candidates: Optional[List[str]] = None,
    top_n: int = 10,
    min_score: float = 0.25,
    weights: Dict[str, float] = None,
) -> List[Dict[str, Any]]:
    """
    Fusion competitor identifier:
      - Candidate orgs from your friend's spaCy NER
      - Scored by your richer competitor signals
      - Optional SBERT name similarity
    Returns list of {name, score, signals, explanation}
    """
    if not seed_brand or not text:
        return []

    # 1) Candidate generation
    friend_orgs = extract_org_candidates(text)
    candidates = friend_orgs[:]
    if extra_candidates:
        for c in extra_candidates:
            if c and c not in candidates:
                candidates.append(c)

    # Deduplicate (case-insensitive), drop the seed brand itself
    seen = set()
    uniq: List[str] = []
    seed_low = seed_brand.lower().strip()
    for c in candidates:
        lc = c.lower().strip()
        if lc and lc != seed_low and lc not in seen:
            seen.add(lc)
            uniq.append(c)

    # 2) Weights (tune later)
    W = {
        "same_sentence": 0.45,     # seed & candidate co-mentioned
        "comp_terms": 0.20,        # co-mention with competitor terms
        "industry_loc": 0.15,      # industry/location hints present
        "domain_hint": 0.05,       # brand-ish name
        "sbert_name": 0.15,        # optional name similarity
    }
    if weights:
        W.update(weights)

    # 3) Score each candidate
    out: List[Dict[str, Any]] = []
    for cand in uniq:
        both, both_comp = _same_sentence_hits(text, seed_brand, cand)
        ss = min(1.0, both / 2.0)        # cap at 2 sentences → 1.0
        cc = min(1.0, both_comp / 1.0)   # any 1+ comp-term sentence → 1.0
        il = _industry_location_boost(text, industry=industry, location=location)
        dh = _domain_hint(cand)
        sb = _sbert_name_sim(seed_brand, cand)

        score = (
            W["same_sentence"] * ss +
            W["comp_terms"]    * cc +
            W["industry_loc"]  * il +
            W["domain_hint"]   * dh +
            W["sbert_name"]    * sb
        )
        score = _clip01(score)

        # Build an explanation
        reasons = []
        if ss >= 0.5: reasons.append(f"co-mentioned with {seed_brand} in multiple sentences")
        elif ss > 0:  reasons.append(f"co-mentioned with {seed_brand}")
        if cc > 0:    reasons.append("appears near competitor language")
        if il > 0:    reasons.append("matches industry/location context")
        if dh > 0:    reasons.append("brand-like name")
        if sb >= 0.6: reasons.append("name similarity to peer brands")

        out.append({
            "name": cand,
            "score": round(float(score), 4),
            "signals": {
                "same_sentence": ss, "comp_terms": cc, "industry_loc": il,
                "domain_hint": dh, "sbert_name": sb
            },
            "explanation": "; ".join(reasons) if reasons else "weak evidence",
        })

    out.sort(key=lambda r: r["score"], reverse=True)
    if min_score is not None:
        out = [r for r in out if r["score"] >= min_score]
    return out[:top_n]
