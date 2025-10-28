from __future__ import annotations
from typing import List, Set
from identify_competitor import KeyPlayerIdentifier  

def extract_org_candidates(text: str, *, spacy_model: str = "en_core_web_sm") -> List[str]:
    kpi = KeyPlayerIdentifier(model_name=spacy_model)
    ents = kpi.identify_key_players(text)
    orgs = [e["text"].strip() for e in ents.get("organizations", []) if e.get("text")]
    seen: Set[str] = set()
    out: List[str] = []
    for o in orgs:
        lo = o.lower()
        if lo and lo not in seen:
            seen.add(lo)
            out.append(o)
    return out
