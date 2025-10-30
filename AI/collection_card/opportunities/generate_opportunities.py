# AI/collection_card/generate_opportunities.py

from __future__ import annotations

import os
import sys
import json
import re
from typing import List, Dict, Any

# Keep your existing shared Groq client shim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gpt  # noqa: E402


# -------------------------------
# Helpers
# -------------------------------


def _coerce_list_of_str(x) -> List[str]:
    if x is None:
        return []
    if isinstance(x, str):
        return [x.strip()] if x.strip() else []
    if isinstance(x, list):
        out = []
        for i in x:
            if isinstance(i, str):
                s = i.strip()
                if s:
                    out.append(s)
            else:
                out.append(str(i))
        return out
    return [str(x)]


def _normalize_articles(
    articles: List[Dict[str, Any]], max_articles: int = 20
) -> List[Dict[str, Any]]:
    """
    Ensure consistent keys and prioritize by relevance then recency.
    Returns top `max_articles`.
    """

    def _safe_float(v, default=0.0):
        try:
            return float(v)
        except Exception:
            return default

    def _safe_int(v, default=0):
        try:
            return int(v)
        except Exception:
            return default

    cleaned = []
    for a in articles or []:
        url = a.get("url") or a.get("uri") or ""
        cleaned.append(
            {
                "ai_title": a.get("ai_title", "") or "",
                "ai_summary": a.get("ai_summary", "") or "",
                "url": url,
                "source": a.get("source", "") or "",
                "relevance_score": _safe_float(a.get("relevance_score"), 0.0),
                "published_ts": _safe_int(a.get("published_ts"), 0),
                "tags": a.get("tags", []) if isinstance(a.get("tags"), list) else [],
            }
        )

    # Sort: high relevance first, then recent
    cleaned.sort(key=lambda r: (r["relevance_score"], r["published_ts"]), reverse=True)

    # Deduplicate by URL/title to avoid prompt bloat
    seen = set()
    out = []
    for r in cleaned:
        key = (r["url"] or r["ai_title"]).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(r)
        if len(out) >= max_articles:
            break
    return out


def _build_prompt(
    company: str,
    description: str,
    competitors: List[str],
    industry_name: str,
    articles: List[Dict[str, Any]],
) -> str:
    """
    Build a concise, LLM-friendly prompt with just enough context to produce actionable, JSON-only output.
    """
    comp_str = ", ".join([c for c in competitors or [] if c]) or "N/A"

    # Tighten article block to keep token count under control
    lines = []
    for i, a in enumerate(articles, 1):
        tags = ", ".join(a.get("tags", []))
        lines.append(
            f"{i}. [{a.get('source', 'Unknown')}] {a.get('ai_title', 'Untitled')}\n"
            f"   Summary: {a.get('ai_summary', 'No summary')}\n"
            f"   URL: {a.get('url', '')}\n"
            f"   Relevance: {a.get('relevance_score', 0):.2f} | Tags: {tags}"
        )
    articles_block = "\n".join(lines) if lines else "None available."

    return f"""
You are a strategic growth analyst for {company}.

Company:
- Name: {company}
- What we do: {description}
- Main competitors: {comp_str}

Industry focus: "{industry_name}"

Recent industry articles (evidence you MUST use):
{articles_block}

TASK:
Identify concrete BUSINESS OPPORTUNITIES for {company} in this industry. Types:
- Partnerships or acquisitions
- New markets/regions
- New product/features to build
- Service gaps competitors aren't covering
- Regulatory/timing windows
- Messaging/positioning angles

STRICT RULES:
- Only use evidence from the articles above.
- Be specific and actionable.
- Each opportunity MUST cite a specific source article/title and URL from the list.
- Prioritize what {company} can realistically do.

OUTPUT:
Return ONLY a valid JSON array. No markdown. No commentary.
Each item must have exactly these keys:

[
  {{
    "opportunity": "Concise, specific opportunity",
    "why_it_matters": "1-2 sentence rationale grounded in the cited article",
    "recommended_action": ["Step 1", "Step 2", "Step 3"],
    "impact": "high" | "medium" | "low",
    "urgency": "now" | "soon" | "watch",
    "source_article": "Exact title from the list above",
    "source_url": "Exact URL from the list above"
  }}
]
If no opportunities are truly supported by the articles, return [].
""".strip()


_JSON_BLOCK = re.compile(r"\[.*\]", re.DOTALL)


def _extract_json(text: str) -> str:
    """
    Pull the first JSON array from possibly chatty LLM text.
    Handles ```json fences and stray commentary.
    """
    if not text:
        return "[]"
    t = text.strip()
    # strip code fences if present
    if t.startswith("```json"):
        t = t[7:]
    if t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    t = t.strip()

    # if it's already a clean JSON array
    if t.startswith("[") and t.endswith("]"):
        return t

    # try to find the first [] block
    m = _JSON_BLOCK.search(t)
    return m.group(0) if m else "[]"


def _rank_opportunities(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Bubble the most urgent/impactful to the top for UI.
    """
    urgency_w = {"now": 3, "soon": 2, "watch": 1}
    impact_w = {"high": 3, "medium": 2, "low": 1}

    def score(it):
        u = urgency_w.get(str(it.get("urgency", "")).lower(), 2)
        im = impact_w.get(str(it.get("impact", "")).lower(), 2)
        return (u, im)

    return sorted(items, key=score, reverse=True)


# -------------------------------
# Main API
# -------------------------------


def generate_opportunities(
    company_context: dict, industry_name: str, industry_articles: list
) -> List[Dict[str, Any]]:
    """
    Turn industry news + company profile into concrete business opportunities.
    Returns a list of dicts:
    {
      "opportunity": str,
      "why_it_matters": str,
      "recommended_action": [str, ...],
      "impact": "high|medium|low",
      "urgency": "now|soon|watch",
      "source_article": str,
      "source_url": str
    }
    """
    # Guard: no articles → nothing to infer
    norm_articles = _normalize_articles(industry_articles or [], max_articles=20)
    if not norm_articles:
        return []

    company_name = company_context.get("company", "").strip()
    description = company_context.get("description", "").strip()
    competitors = company_context.get("competitors", []) or []

    prompt = _build_prompt(
        company=company_name,
        description=description,
        competitors=competitors,
        industry_name=industry_name,
        articles=norm_articles,
    )

    # Keep LLM focused and under token budget
    raw = gpt.load_model(
        prompt,
        max_tokens=2200,  # plenty for 10–15 good items
        temperature=0.30,  # crisp, business-like
        stream=False,
    )

    json_str = _extract_json(raw)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        # If the model still returns junk, fail soft with []
        return []

    if not isinstance(data, list):
        return []

    # Normalize + coerce shapes
    cleaned: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        cleaned.append(
            {
                "opportunity": (item.get("opportunity") or "").strip(),
                "why_it_matters": (item.get("why_it_matters") or "").strip(),
                "recommended_action": _coerce_list_of_str(
                    item.get("recommended_action")
                ),
                "impact": (item.get("impact") or "medium").strip().lower(),
                "urgency": (item.get("urgency") or "soon").strip().lower(),
                "source_article": (item.get("source_article") or "").strip(),
                "source_url": (item.get("source_url") or "").strip(),
            }
        )

    # Filter obviously empty rows & dedupe by (source_url, opportunity)
    seen = set()
    final = []
    for it in cleaned:
        if not it["opportunity"] or not it["source_url"]:
            continue
        key = (it["source_url"].lower(), it["opportunity"].lower())
        if key in seen:
            continue
        seen.add(key)
        final.append(it)

    # Rank best to top (urgency + impact)
    final = _rank_opportunities(final)

    return final
