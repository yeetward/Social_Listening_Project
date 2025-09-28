# AI/Algorithms/engagement_scorer.py
"""
Heuristic engagement score based on likes/comments/shares
Scales to [0,1] with a soft saturation to avoid one viral post dominating.
"""

from typing import Dict


def engagement_score(doc: Dict) -> float:
    e = doc.get("engagement") or {}
    likes = max(0, int(e.get("likes", 0)))
    comments = max(0, int(e.get("comments", 0)))
    shares = max(0, int(e.get("shares", 0))) # reposts

    # tune weights to taste / source:
    raw = likes * 1 + comments * 3 + shares * 4

    # soft-cap (squash) so the function approaches 1.0
    # increase the constant to make saturation slower.
    score = raw / (raw + 50.0)

    # clamp
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return float(score)
