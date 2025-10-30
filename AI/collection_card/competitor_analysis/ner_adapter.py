# from __future__ import annotations
# from typing import List, Set
# from .identify_competitor import KeyPlayerIdentifier

# def extract_org_candidates(text: str, *, spacy_model: str = "en_core_web_sm") -> List[str]:
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

# AI/ner_adapter.py
from __future__ import annotations
from typing import List, Set
import re

try:
    from .identify_competitor import KeyPlayerIdentifier

    _HAS_FRIEND = True
except Exception:
    _HAS_FRIEND = False

_SUFFIXES = re.compile(r"\b(inc\.?|ltd\.?|llc\.?|plc|corp\.?|co\.?)\b", re.IGNORECASE)
_CAP_SEQ = re.compile(
    r"(?:\b[A-Z][a-zA-Z0-9&\-]+\b(?:\s+\b[A-Z][a-zA-Z0-9&\-]+\b){0,3})"
)


def _clean_brand(s: str) -> str:
    s = (s or "").strip()
    s = _SUFFIXES.sub("", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip(" .,-–—")


def _regex_org_candidates(text: str) -> List[str]:
    return _CAP_SEQ.findall(text or "")


def extract_org_candidates(
    text: str, *, spacy_model: str = "en_core_web_sm"
) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []

    if _HAS_FRIEND:
        try:
            kpi = KeyPlayerIdentifier(model_name=spacy_model)
            ents = kpi.identify_key_players(text)
            for e in ents.get("organizations", []):
                c = _clean_brand((e.get("text") or "").strip())
                lo = c.lower()
                if lo and lo not in seen:
                    seen.add(lo)
                    out.append(c)
        except Exception:
            pass

    if not out:  # fallback
        for o in _regex_org_candidates(text):
            c = _clean_brand(o)
            lo = c.lower()
            if lo and lo not in seen:
                seen.add(lo)
                out.append(c)

    return out
