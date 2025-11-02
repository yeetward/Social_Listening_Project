# # AI/collection_card/analyse_backlinks.py

# from __future__ import annotations
# from typing import Dict, Any, List
# import math
# import json
# import gpt


# def score_backlink_metrics(bl: Dict[str, Any]) -> float:
#     """
#     Heuristic numeric score 0..1 for a backlink.
#     Factors:
#     - domain authority (0-100 scale-ish)
#     - estimated traffic / clicks
#     - is it dofollow?
#     - anchor text relevance boost
#     """
#     da = float(bl.get("domain_authority", 0))
#     traffic = float(bl.get("estimated_monthly_clicks", 0))
#     dofollow = bool(bl.get("dofollow", True))
#     anchor = (bl.get("anchor_text") or "").lower()

#     # normalize DA ~0..1 by dividing by 100, cap at 1
#     da_score = min(1.0, da / 100.0)

#     # traffic saturates; use soft curve so big sites don't blow everything up
#     traffic_score = traffic / (traffic + 100.0)  # ~0..1

#     # follow links are more valuable for SEO than nofollow
#     follow_bonus = 0.15 if dofollow else 0.0

#     # anchor relevance guess:
#     # "ai marketing", "automation", etc. You can tune these keywords per client.
#     relevance_keywords = ["ai", "automation", "marketing", "platform", "insights"]
#     rel_hit = any(kw in anchor for kw in relevance_keywords)
#     anchor_bonus = 0.15 if rel_hit else 0.0

#     raw = da_score * 0.5 + traffic_score * 0.35 + follow_bonus + anchor_bonus
#     # clamp
#     if raw < 0.0:
#         return 0.0
#     if raw > 1.0:
#         return 1.0
#     return float(raw)


# def llm_classify_backlink(
#     backlink: Dict[str, Any],
#     company_name: str,
#     temperature: float = 0.2,
#     max_tokens: int = 250,
# ) -> Dict[str, Any]:
#     """
#     Use LLM to label backlink sentiment/category and generate a short marketing note.
#     Output:
#     {
#       "sentiment": "positive" | "neutral" | "negative",
#       "category": "press" | "partner" | "influencer" | "competitor" | "directory",
#       "summary": "..."
#     }
#     """
#     prompt = f"""
# You are an AI marketing & PR analyst.

# Company: {company_name}

# We found an external backlink pointing to the company.

# Source domain: {backlink.get("source_domain")}
# Source URL: {backlink.get("source_url")}
# Anchor text pointing to the company: "{backlink.get("anchor_text")}"

# Task:
# 1. Classify sentiment toward the company as "positive", "neutral", or "negative".
# 2. Classify source type as one of:
#    - "press" (media / news / PR coverage)
#    - "partner" (business partner, integration, affiliate)
#    - "influencer" (personal blog, social, thought leader)
#    - "competitor" (comparison, vs us, competitor marketing page)
#    - "directory" (generic directory / low-value listing)
# 3. Give a one-sentence summary of why this backlink could matter to marketing or sales.

# Return ONLY valid JSON. Example:
# {{
#   "sentiment": "positive",
#   "category": "press",
#   "summary": "Industry media coverage framing us as an AI leader in marketing automation."
# }}
# """

#     # call your shared Groq-based LLM wrapper
#     raw = gpt.load_model(
#         prompt, max_tokens=max_tokens, temperature=temperature, stream=False
#     )

#     try:
#         enriched = json.loads(raw)
#         if not isinstance(enriched, dict):
#             raise ValueError("Expected dict JSON from LLM.")
#         # lightweight cleanup / fallback defaults
#         return {
#             "sentiment": enriched.get("sentiment", "neutral"),
#             "category": enriched.get("category", "directory"),
#             "summary": enriched.get("summary", "").strip() or "No summary provided.",
#         }
#     except Exception:
#         # If the model returns junk, we fail safely
#         return {
#             "sentiment": "neutral",
#             "category": "directory",
#             "summary": "LLM enrichment unavailable or returned invalid format.",
#         }


# def analyse_backlinks(
#     backlinks: List[Dict[str, Any]],
#     company_name: str,
#     top_n: int = 20,
#     with_llm: bool = True,
# ) -> List[Dict[str, Any]]:
#     """
#     Score + (optionally) enrich each backlink.
#     Returns sorted list with fields prepared for Mongo/UI.
#     """
#     scored_items: List[Dict[str, Any]] = []

#     for bl in backlinks:
#         base_score = score_backlink_metrics(bl)

#         enrichment = (
#             llm_classify_backlink(bl, company_name)
#             if with_llm
#             else {
#                 "sentiment": "neutral",
#                 "category": "directory",
#                 "summary": "LLM enrichment disabled.",
#             }
#         )

#         scored_items.append(
#             {
#                 # core backlink info
#                 "source_url": bl.get("source_url"),
#                 "source_domain": bl.get("source_domain"),
#                 "target_url": bl.get("target_url"),
#                 "anchor_text": bl.get("anchor_text", ""),
#                 "dofollow": bool(bl.get("dofollow", True)),
#                 # numeric signals
#                 "estimated_monthly_clicks": bl.get("estimated_monthly_clicks", 0),
#                 "domain_authority": bl.get("domain_authority", 0),
#                 # AI scores
#                 "relevance_score": base_score,
#                 "sentiment": enrichment["sentiment"],
#                 "category": enrichment["category"],
#                 "ai_summary": enrichment["summary"],
#             }
#         )

#     # sort by our base_score (relevance_score) desc
#     scored_items.sort(key=lambda x: x["relevance_score"], reverse=True)

#     return scored_items[:top_n]


# from __future__ import annotations
# from typing import Dict, Any, List
# import json
# import gpt


# def score_backlink_metrics(bl: Dict[str, Any]) -> float:
#     """
#     Heuristic 0..1 score for a backlink:
#       - domain authority (0..100 → ~0..1)
#       - estimated traffic (soft saturation)
#       - dofollow bonus
#       - anchor relevance bonus (keyword hit)
#     """
#     da = float(bl.get("domain_authority", 0))
#     traffic = float(bl.get("estimated_monthly_clicks", 0))
#     dofollow = bool(bl.get("dofollow", True))
#     anchor = (bl.get("anchor_text") or "").lower()

#     da_score = min(1.0, da / 100.0)
#     traffic_score = traffic / (traffic + 100.0)  # 0..1 soft cap
#     follow_bonus = 0.15 if dofollow else 0.0

#     relevance_keywords = ["ai", "automation", "marketing", "platform", "insights"]
#     anchor_bonus = 0.15 if any(kw in anchor for kw in relevance_keywords) else 0.0

#     raw = da_score * 0.5 + traffic_score * 0.35 + follow_bonus + anchor_bonus
#     return max(0.0, min(1.0, float(raw)))


# def llm_classify_backlink(
#     backlink: Dict[str, Any],
#     company_name: str,
#     temperature: float = 0.2,
#     max_tokens: int = 250,
# ) -> Dict[str, Any]:
#     """
#     Use LLM to label sentiment/category and generate a short note.
#     Returns dict with: sentiment, category, summary
#     """
#     prompt = f"""
# You are an AI marketing & PR analyst.

# Company: {company_name}

# We found an external backlink pointing to the company.

# Source domain: {backlink.get("source_domain")}
# Source URL: {backlink.get("source_url")}
# Anchor text pointing to the company: "{backlink.get("anchor_text")}"

# Task:
# 1) Classify sentiment: "positive", "neutral", or "negative".
# 2) Classify source type as one of: "press", "partner", "influencer", "competitor", "directory".
# 3) One-sentence why this backlink could matter to marketing or sales.

# Return ONLY valid JSON:
# {{
#   "sentiment": "positive",
#   "category": "press",
#   "summary": "Industry media coverage framing us as an AI leader in marketing automation."
# }}
# """
#     raw = gpt.load_model(
#         prompt, max_tokens=max_tokens, temperature=temperature, stream=False
#     )
#     try:
#         enriched = json.loads(raw)
#         if not isinstance(enriched, dict):
#             raise ValueError("Expected dict JSON from LLM.")
#         return {
#             "sentiment": enriched.get("sentiment", "neutral"),
#             "category": enriched.get("category", "directory"),
#             "summary": (enriched.get("summary") or "No summary provided.").strip(),
#         }
#     except Exception:
#         return {
#             "sentiment": "neutral",
#             "category": "directory",
#             "summary": "LLM enrichment unavailable or invalid format.",
#         }


# def analyse_backlinks(
#     backlinks: List[Dict[str, Any]],
#     company_name: str,
#     top_n: int = 20,
#     with_llm: bool = True,
# ) -> List[Dict[str, Any]]:
#     """
#     Score + (optionally) enrich each backlink.
#     Returns sorted list for Mongo/UI.
#     """
#     items: List[Dict[str, Any]] = []
#     for bl in backlinks:
#         base_score = score_backlink_metrics(bl)
#         enrichment = (
#             llm_classify_backlink(bl, company_name)
#             if with_llm
#             else {
#                 "sentiment": "neutral",
#                 "category": "directory",
#                 "summary": "LLM enrichment disabled.",
#             }
#         )
#         items.append(
#             {
#                 "source_url": bl.get("source_url"),
#                 "source_domain": bl.get("source_domain"),
#                 "target_url": bl.get("target_url"),
#                 "anchor_text": bl.get("anchor_text", ""),
#                 "dofollow": bool(bl.get("dofollow", True)),
#                 "estimated_monthly_clicks": bl.get("estimated_monthly_clicks", 0),
#                 "domain_authority": bl.get("domain_authority", 0),
#                 "relevance_score": base_score,
#                 "sentiment": enrichment["sentiment"],
#                 "category": enrichment["category"],
#                 "ai_summary": enrichment["summary"],
#             }
#         )
#     items.sort(key=lambda x: x["relevance_score"], reverse=True)
#     return items[:top_n]


# # AI/collection_card/analyse_backlinks.py

# from __future__ import annotations
# from typing import Dict, Any, List
# import json
# import gpt


# def score_backlink_metrics(bl: Dict[str, Any]) -> float:
#     da = float(bl.get("domain_authority", 0))
#     traffic = float(bl.get("estimated_monthly_clicks", 0))
#     dofollow = bool(bl.get("dofollow", True))
#     anchor = (bl.get("anchor_text") or "").lower()

#     da_score = min(1.0, da / 100.0)
#     traffic_score = traffic / (traffic + 100.0)  # soft saturation
#     follow_bonus = 0.15 if dofollow else 0.0

#     relevance_keywords = ["ai", "automation", "marketing", "platform", "insights"]
#     anchor_bonus = 0.15 if any(kw in anchor for kw in relevance_keywords) else 0.0

#     raw = da_score * 0.5 + traffic_score * 0.35 + follow_bonus + anchor_bonus
#     return max(0.0, min(1.0, float(raw)))


# def llm_classify_backlink(
#     backlink: Dict[str, Any],
#     company_name: str,
#     temperature: float = 0.2,
#     max_tokens: int = 250,
# ) -> Dict[str, Any]:
#     prompt = f"""
# You are an AI marketing & PR analyst.

# Company: {company_name}

# We found an external backlink referencing the company.

# Source domain: {backlink.get("source_domain")}
# Source URL: {backlink.get("source_url")}
# Anchor text: "{backlink.get("anchor_text")}"

# Task:
# 1) sentiment: "positive" | "neutral" | "negative"
# 2) category: "press" | "partner" | "influencer" | "competitor" | "directory"
# 3) summary: one sentence on why this backlink matters.

# Return ONLY JSON:
# {{"sentiment":"positive","category":"press","summary":"..."}}"""
#     raw = gpt.load_model(
#         prompt, max_tokens=max_tokens, temperature=temperature, stream=False
#     )
#     try:
#         out = json.loads(raw)
#         if not isinstance(out, dict):
#             raise ValueError("Expected dict JSON")
#         return {
#             "sentiment": out.get("sentiment", "neutral"),
#             "category": out.get("category", "directory"),
#             "summary": (out.get("summary") or "").strip() or "No summary provided.",
#         }
#     except Exception:
#         return {
#             "sentiment": "neutral",
#             "category": "directory",
#             "summary": "LLM enrichment unavailable or invalid JSON.",
#         }


# def analyse_backlinks(
#     backlinks: List[Dict[str, Any]],
#     company_name: str,
#     top_n: int = 20,
#     with_llm: bool = True,
# ) -> List[Dict[str, Any]]:
#     items: List[Dict[str, Any]] = []
#     for bl in backlinks:
#         base = score_backlink_metrics(bl)
#         enr = (
#             llm_classify_backlink(bl, company_name)
#             if with_llm
#             else {
#                 "sentiment": "neutral",
#                 "category": "directory",
#                 "summary": "LLM enrichment disabled.",
#             }
#         )
#         items.append(
#             {
#                 "source_url": bl.get("source_url"),
#                 "source_domain": bl.get("source_domain"),
#                 "target_url": bl.get("target_url"),  # may be None
#                 "anchor_text": bl.get("anchor_text", ""),
#                 "dofollow": bool(bl.get("dofollow", True)),
#                 "estimated_monthly_clicks": bl.get("estimated_monthly_clicks", 0),
#                 "domain_authority": bl.get("domain_authority", 0),
#                 "relevance_score": base,
#                 "sentiment": enr["sentiment"],
#                 "category": enr["category"],
#                 "ai_summary": enr["summary"],
#             }
#         )
#     items.sort(key=lambda x: x["relevance_score"], reverse=True)
#     return items[:top_n]















from __future__ import annotations
from typing import Dict, Any, List
import math
import json

try:
    import gpt  # your shared Groq wrapper (optional)
except Exception:
    gpt = None


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _recency_score(age_days: float) -> float:
    # half-life ~30 days: fresh content gets boosted
    return math.exp(-max(0.0, age_days) / 30.0)


def _title_click_score(title: str) -> float:
    # very lightweight "click potential" heuristic
    t = (title or "").strip()
    if not t:
        return 0.0
    # length in a sweet spot ~35..95 chars
    length_term = 1.0 - abs(len(t) - 65) / 65.0
    length_term = max(0.0, min(1.0, length_term))
    # contains numbers or strong verbs gets a nudge
    has_num = any(ch.isdigit() for ch in t)
    verbs = ["reveals", "wins", "launches", "raises", "acquires", "partners", "joins", "beats"]
    verb_hit = any(v in t.lower() for v in verbs)
    bump = 0.1 * has_num + 0.1 * verb_hit
    return max(0.0, min(1.0, length_term + bump))


def score_backlink_item(bl: Dict[str, Any]) -> float:
    """
    Engagement-oriented score:
      - Social sources prioritized
      - Fresher is better
      - Higher relevance_score from enrichment pipeline
      - Clickable title heuristic
    """
    is_social = bool(bl.get("is_social"))
    rel = float(bl.get("relevance_score", 0.0))
    age_days = bl.get("_age_days", 60.0)
    rec = _recency_score(age_days)
    title_click = _title_click_score(bl.get("ai_title", ""))

    # weights tuned for "engage now" behavior
    return (
        0.38 * (1.0 if is_social else 0.0) +
        0.27 * rec +
        0.22 * _sigmoid(3.0 * (rel - 0.35)) +
        0.13 * title_click
    )


def _llm_enrich(backlink: Dict[str, Any], company_name: str) -> Dict[str, Any]:
    """
    Optional LLM labeling (sentiment/category + 1-liner).
    If gpt wrapper is missing or returns junk, safe fallback.
    """
    if not gpt:
        return {"sentiment": "neutral", "category": "mention", "summary": "LLM enrichment disabled."}

    prompt = f"""
You are an AI marketing & PR analyst.

Company: {company_name}

We found a post that mentions or discusses the company.

Source domain: {backlink.get('source_domain')}
Source URL: {backlink.get('source_url')}
Title: {backlink.get('ai_title')}
Summary: {backlink.get('ai_summary')}

Task:
1. Sentiment toward the company: "positive", "neutral", or "negative".
2. Source type: "social", "press", "blog", "directory", or "forum".
3. One-sentence marketing note on how to engage with this post.

Return ONLY valid JSON like:
{{
  "sentiment": "positive",
  "category": "social",
  "summary": "High-visibility LinkedIn post; reshare + comment within 24h to capture recency."
}}
""".strip()

    try:
        raw = gpt.load_model(prompt, max_tokens=220, temperature=0.2, stream=False)
        enriched = json.loads(raw)
        if not isinstance(enriched, dict):
            raise ValueError("Expected dict JSON")
        return {
            "sentiment": enriched.get("sentiment", "neutral"),
            "category": enriched.get("category", "blog"),
            "summary": (enriched.get("summary") or "").strip() or "No summary provided.",
        }
    except Exception:
        return {"sentiment": "neutral", "category": "blog", "summary": "LLM enrichment unavailable."}


def analyse_backlinks(
    items: List[Dict[str, Any]],
    *,
    company_name: str,
    with_llm: bool = False,
    now_ts: int | None = None,
    top_n: int = 20,
) -> List[Dict[str, Any]]:
    """
    Score + (optional) LLM enrich, return engagement-ready list with real source_url.
    """
    if not items:
        return []

    # compute age (days) once
    import time
    _now = int(now_ts or time.time())
    for it in items:
        ts = int(it.get("published_ts", _now))
        it["_age_days"] = max(0, (_now - ts) / 86400.0)

    scored: List[Dict[str, Any]] = []
    for bl in items:
        score = score_backlink_item(bl)
        enrichment = _llm_enrich(bl, company_name) if with_llm else {
            "sentiment": "neutral", "category": "mention", "summary": "Engage where relevant."
        }

        scored.append({
            "source_url": bl.get("source_url"),
            "source_domain": bl.get("source_domain"),
            "title": bl.get("ai_title", ""),
            "summary": bl.get("ai_summary", ""),
            "published_ts": bl.get("published_ts"),
            "tags": bl.get("tags", []),
            "is_social": bl.get("is_social", False),

            # signals
            "relevance_score": bl.get("relevance_score", 0.0),
            "engagement_score": round(float(score), 4),

            # AI labels
            "sentiment": enrichment["sentiment"],
            "category": enrichment["category"],
            "ai_note": enrichment["summary"],

            # suggested action (no LLM dependency)
            "action": (
                "Comment + reshare now" if bl.get("is_social")
                else "Reach out to author or share in newsroom"
            ),
        })

    scored.sort(key=lambda x: x["engagement_score"], reverse=True)
    return scored[:top_n]

