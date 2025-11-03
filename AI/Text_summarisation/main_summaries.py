<<<<<<< Updated upstream
# AI/collection_card/main_summaries.py
# AI/Text_summarisation/main_summaries.py
from __future__ import annotations
import re
from collections import Counter
from typing import List

_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')
_WORD = re.compile(r"[A-Za-z0-9]+")

def _sentences(text: str) -> List[str]:
    s = (text or "").strip()
    if not s:
        return []
    return _SENT_SPLIT.split(s)
=======
# AI/Text_summarisation/main_summaries.py
"""
Simple text summarization function.
Accepts text and returns a 4-line summary without using LLM.
"""
from __future__ import annotations
from AI.Text_summarisation.Text_summariser import summarize_text
>>>>>>> Stashed changes

def _tokens(s: str) -> List[str]:
    return _WORD.findall((s or "").lower())

<<<<<<< Updated upstream
def _score_sentences(sents: List[str]) -> List[tuple]:
    # word frequency scoring (stopword-lite)
    stop = {
        "the","a","an","and","or","but","if","then","else","when","while","is","of","to","in","for",
        "on","by","with","as","at","from","that","this","it","its","be","are","was","were","has","had",
        "have","not","no","we","you","they","he","she","them","his","her","their","our","i"
    }
    words = []
    for s in sents:
        words.extend([w for w in _tokens(s) if w not in stop and len(w) > 2])
    if not words:
        return [(i, 0.0) for i,_ in enumerate(sents)]

    freq = Counter(words)
    maxf = max(freq.values())
    # normalize freq
    for k in list(freq.keys()):
        freq[k] = freq[k] / maxf

    scored = []
    for i, s in enumerate(sents):
        toks = [w for w in _tokens(s) if w in freq]
        score = sum(freq[w] for w in toks)
        # slight length penalty to avoid very long sentences dominating
        score = score / max(1.0, len(toks))
        scored.append((i, score))
    return scored

def run(text: str, max_sents: int = 3) -> str:
    """
    Simple, fast, extractive summary (no LLM).
    Picks top-k sentences by normalized word-frequency salience, keeps original order.
    """
    sents = _sentences(text)
    if not sents:
        return ""

    scored = _score_sentences(sents)
    # pick top-k by score
    top = sorted(scored, key=lambda x: x[1], reverse=True)[:max_sents]
    # restore original order
    top_idx = sorted([i for i,_ in top])
    out = " ".join(sents[i].strip() for i in top_idx if sents[i].strip())
    return out.strip()
=======
def generate_summary(text: str) -> str:
    """
    Generate a 4-line summary from any text input.

    Args:
        text: The input text to summarize (can be large)

    Returns:
        A string containing 4 sentences summarizing the key points

    Example:
        >>> article = "Long article text here..."
        >>> summary = generate_summary(article)
        >>> print(summary)
    """
    return summarize_text(text, num_sentences=4)
>>>>>>> Stashed changes
