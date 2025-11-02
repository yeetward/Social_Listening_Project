# from __future__ import annotations
# from typing import List, Set
# from .identify_competitor import KeyPlayerIdentifier


# def extract_org_candidates(
#     text: str, *, spacy_model: str = "en_core_web_sm"
# ) -> List[str]:
#     kpi = KeyPlayerIdentifier(model_name=spacy_model)
#     ents = kpi.identify_key_players(text)
#     orgs = [e["text"].strip() for e in ents.get("organizations", []) if e.get("text")]
#     seen: Set[str] = set()
#     out: List[str] = []
#     for o in orgs:
#         lo = o.lower()
#         if lo and lo not in seen:
#             seen.add(lo)
#             out.append(o)
#     return out

# ---------------------------------------------

# # AI/ner_adapter.py
# from __future__ import annotations
# from typing import List, Set
# import re

# try:
#     from .identify_competitor import KeyPlayerIdentifier

#     _HAS_FRIEND = True
# except Exception:
#     _HAS_FRIEND = False

# _SUFFIXES = re.compile(r"\b(inc\.?|ltd\.?|llc\.?|plc|corp\.?|co\.?)\b", re.IGNORECASE)
# _CAP_SEQ = re.compile(
#     r"(?:\b[A-Z][a-zA-Z0-9&\-]+\b(?:\s+\b[A-Z][a-zA-Z0-9&\-]+\b){0,3})"
# )


# def _clean_brand(s: str) -> str:
#     s = (s or "").strip()
#     s = _SUFFIXES.sub("", s)
#     s = re.sub(r"\s{2,}", " ", s)
#     return s.strip(" .,-–—")


# def _regex_org_candidates(text: str) -> List[str]:
#     return _CAP_SEQ.findall(text or "")


# def extract_org_candidates(
#     text: str, *, spacy_model: str = "en_core_web_sm"
# ) -> List[str]:
#     seen: Set[str] = set()
#     out: List[str] = []

#     if _HAS_FRIEND:
#         try:
#             kpi = KeyPlayerIdentifier(model_name=spacy_model)
#             ents = kpi.identify_key_players(text)
#             for e in ents.get("organizations", []):
#                 c = _clean_brand((e.get("text") or "").strip())
#                 lo = c.lower()
#                 if lo and lo not in seen:
#                     seen.add(lo)
#                     out.append(c)
#         except Exception:
#             pass

#     if not out:  # fallback
#         for o in _regex_org_candidates(text):
#             c = _clean_brand(o)
#             lo = c.lower()
#             if lo and lo not in seen:
#                 seen.add(lo)
#                 out.append(c)

#     return out


#--------------------------------------



# AI/competitors/ner_adapter.py
from __future__ import annotations
from typing import List, Set
import re

# Try spaCy, fall back gracefully if unavailable
try:
    import spacy
    _NLP = spacy.load("en_core_web_sm")
except Exception:
    _NLP = None

# Simple domain-ish detector (skip urls/emails as org candidates)
_URL_RE = re.compile(r"https?://|www\.|[\w\.-]+@\w+")
# TitleCase tokens or ALLCAPS chunks often indicate orgs
_TITLE_TOKEN = re.compile(r"(?:[A-Z][a-z0-9&@’'\-]+)(?:\s+[A-Z][a-z0-9&@’'\-]+)*")


def _regex_orgs(text: str) -> List[str]:
    """Very light fallback extraction when spaCy isn't installed."""
    out: List[str] = []
    seen: Set[str] = set()
    for m in _TITLE_TOKEN.finditer(text or ""):
        cand = m.group(0).strip()
        if len(cand) < 2:
            continue
        if _URL_RE.search(cand):
            continue
        lc = cand.lower()
        if lc not in seen:
            seen.add(lc)
            out.append(cand)
    return out


def extract_org_candidates(text: str) -> List[str]:
    """
    Return a de-duplicated list of organization-like strings from text.
    Prefers spaCy ORG entities; falls back to regex if spaCy is absent.
    """
    if not text:
        return []
    if _NLP is None:
        return _regex_orgs(text)

    doc = _NLP(text)
    out: List[str] = []
    seen: Set[str] = set()
    # Prefer ORG; allow PRODUCT as occasional brand proxy
    for ent in doc.ents:
        if ent.label_ in ("ORG", "PRODUCT", "COMPANY"):
            cand = ent.text.strip()
            if not cand or _URL_RE.search(cand):
                continue
            lc = cand.lower()
            if lc not in seen:
                seen.add(lc)
                out.append(cand)
    # Fallback augment with regex if spaCy found too little
    if len(out) < 3:
        for cand in _regex_orgs(text):
            lc = cand.lower()
            if lc not in seen:
                seen.add(lc)
                out.append(cand)
    return out