# AI/Algorithms/engagement_scorer.py
# """
# Heuristic engagement score based on likes/comments/shares
# Scales to [0,1] with a soft saturation to avoid one viral post dominating.
# """

# from typing import Dict


# def engagement_score(doc: Dict) -> float:
#     """
#     Heuristic engagement score scaled to [0,1].

#     Tries multiple common fields so different sources (Reddit, News, etc.)
#     still generate a reasonable engagement signal.
#     """
#     # in engagement_scorer.py (optional tiny tweak at top of engagement_score)
#     e = doc.get("engagement") or {}
#     if not e and doc.get("source") in ("news","rss"):
#         return 0.05   # tiny baseline so pure-news doesn’t get 0.0


#     # flexible extraction
#     likes = max(0, int(e.get("likes", e.get("upvotes", e.get("score", 0)))))
#     comments = max(0, int(e.get("comments", e.get("num_comments", 0))))
#     shares = max(0, int(e.get("shares", e.get("retweets", e.get("reposts", 0)))))

#     # tune weights to taste
#     raw = likes * 1 + comments * 3 + shares * 4

#     # soft saturation so 1 viral post doesn't dominate
#     score = raw / (raw + 50.0)

#     if score < 0.0:
#         return 0.0
#     if score > 1.0:
#         return 1.0
#     return float(score)

"""
Heuristic engagement score based on likes/comments/shares/views.
Scales to [0,1] with soft saturation so one viral post doesn't dominate.
"""

from typing import Dict, Any

def _first_int(d: Dict[str, Any], keys: list[str], default: int = 0) -> int:
    for k in keys:
        if k in d:
            try:
                v = d[k]
                # handle nested like {"count": 123}
                if isinstance(v, dict) and "count" in v:
                    v = v["count"]
                return max(0, int(v))
            except Exception:
                continue
    return default

def engagement_score(doc: Dict[str, Any]) -> float:
    """
    Accepts a doc with a variety of possible engagement containers:
      - doc["engagement"]
      - doc["stats"]
      - doc["metrics"]
      - doc["meta"].get("engagement")
    Supported field aliases (best-effort):
      likes:    likes, like_count, favorites, favorite_count, reactions, reactionCount,
                upvotes, score, points
      comments: comments, comment_count, num_comments, replies, reply_count, discussionCount
      shares:   shares, share_count, retweets, reposts, reshare_count
      views:    views, view_count, impressions, impression_count
    """
    e = (
        doc.get("engagement")
        or doc.get("stats")
        or doc.get("metrics")
        or (doc.get("meta") or {}).get("engagement")
        or {}
    )

    likes = _first_int(e, [
        "likes", "like_count", "favorites", "favorite_count",
        "reactions", "reactionCount", "upvotes", "score", "points",
    ], default=0)

    comments = _first_int(e, [
        "comments", "comment_count", "num_comments", "replies",
        "reply_count", "discussionCount",
    ], default=0)

    shares = _first_int(e, [
        "shares", "share_count", "retweets", "reposts", "reshare_count",
    ], default=0)

    views = _first_int(e, [
        "views", "view_count", "impressions", "impression_count",
    ], default=0)

    # weights: comments>shares>likes, plus a small view signal
    raw = likes * 1 + comments * 3 + shares * 4 + min(views / 200.0, 1000)

    # soft saturation (bigger K => flatter curve)
    K = 100.0
    score = raw / (raw + K)

    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return float(score)
