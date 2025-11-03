# import sys
# import os

# # Add the AI directory to Python path
# current_dir = os.path.dirname(os.path.abspath(__file__))
# ai_dir = os.path.dirname(current_dir)  # Go up to AI directory
# sys.path.insert(0, ai_dir)

# from collection_card.gpt import load_model

# def detect_topic_simple(text:str) -> str:
#     return "topic"# AI/Topic_detection/Topic_detection.py
from __future__ import annotations
import re
from collections import Counter

_WORD = re.compile(r"[A-Za-z0-9]+")

_STOP = {
    "the","a","an","and","or","but","if","then","else","when","while","is","of","to","in","for",
    "on","by","with","as","at","from","that","this","it","its","be","are","was","were","has","had",
    "have","not","no","we","you","they","he","she","them","his","her","their","our","i",
    "will","would","can","could","may","might","should","also","about","into","over","under"
}

def detect_topic_simple(text: str, max_terms: int = 4) -> str:
    """
    Picks top informative terms as a compact topic label.
    """
    toks = [t.lower() for t in _WORD.findall(text or "") if t]
    toks = [t for t in toks if t not in _STOP and len(t) > 2]
    if not toks:
        return ""
    freq = Counter(toks)
    top = [w for w,_ in freq.most_common(8)]
    # de-duplicate stems crudely
    seen = set()
    label_terms = []
    for w in top:
        stem = w[:5]
        if stem not in seen:
            seen.add(stem)
            label_terms.append(w)
        if len(label_terms) >= max_terms:
            break
    return " ".join(label_terms).title()
