# AI/Algorithms/engagement_scorer.py
"""
Heuristic engagement score based on likes/comments/shares
Scales to [0,1] with a soft saturation to avoid one viral post dominating.
"""

from typing import Dict


def engagement_score(doc: Dict) -> float:
    """
    Heuristic engagement score scaled to [0,1].

    Tries multiple common fields so different sources (Reddit, News, etc.)
    still generate a reasonable engagement signal.
    """
    e = doc.get("engagement") or {}

    # flexible extraction
    likes = max(0, int(e.get("likes", e.get("upvotes", e.get("score", 0)))))
    comments = max(0, int(e.get("comments", e.get("num_comments", 0))))
    shares = max(0, int(e.get("shares", e.get("retweets", e.get("reposts", 0)))))

    # tune weights to taste
    raw = likes * 1 + comments * 3 + shares * 4

    # soft saturation so 1 viral post doesn't dominate
    score = raw / (raw + 50.0)

    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return float(score)

