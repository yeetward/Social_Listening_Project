# AI/collection_card/generate_opportunities.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import gpt  # same client pattern you're already using in trending_topics + ideas


def generate_opportunities(company_context: dict, industry_name: str, industry_articles: list):
    """
    Turn industry news + company profile into concrete business opportunities.

    Args:
        company_context: {
            "company": str,
            "description": str,
            "competitors": [str, ...]
        }
        industry_name: str, e.g. "renewable energy", "AI in healthcare"
        industry_articles: list of dicts from fetch_industry_articles:
            {
                "ai_title": str,
                "ai_summary": str,
                "url": str,
                "source": str,
                "relevance_score": float,
                "published_ts": number,
                "tags": [str] (optional)
            }

    Returns:
        list[ dict ] with:
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

    company_name = company_context["company"]
    description = company_context["description"]
    competitors = ", ".join(company_context.get("competitors", []))

    # Format the article batch as context for the LLM
    # (we include relevance_score so the model can prioritise)
    articles_block = ""
    for idx, art in enumerate(industry_articles[:20], 1):
        articles_block += (
            f"\n{idx}. [{art.get('source', 'Unknown Source')}] {art.get('ai_title', 'Untitled')}\n"
            f"   Summary: {art.get('ai_summary', 'No summary')}\n"
            f"   URL: {art.get('url', 'N/A')}\n"
            f"   Relevance: {art.get('relevance_score', 0):.2f}\n"
            f"   Tags: {', '.join(art.get('tags', [])) if isinstance(art.get('tags'), list) else art.get('tags', '')}\n"
        )

    prompt = f"""
You are a strategic growth analyst for {company_name}.

Company:
- Name: {company_name}
- What we do: {description}
- Main competitors: {competitors}

Industry focus for this analysis: "{industry_name}"

Below are recent high-signal industry articles:
{articles_block}

Your job:
Identify concrete BUSINESS OPPORTUNITIES relevant to {company_name} in this industry.
Types of opportunities:
- Potential partnerships or acquisitions
- New market / region expansion plays
- New product or feature we should build
- Service gaps competitors aren't covering
- Regulatory or timing windows we could exploit
- Messaging/positioning angles to own in this space

Important rules:
- ONLY use evidence from the articles provided.
- Be specific. No generic "innovate in AI" answers.
- Tie every opportunity back to something from a specific article.
- Prioritise what {company_name} can ACTUALLY do.

OUTPUT FORMAT:
Return ONLY a valid JSON array, with NO markdown, NO commentary.
Each item in the array must look like this (use real info from above):

[
  {{
    "opportunity": "Partner with XYZ Robotics to offer joint AI-driven warehouse automation to mid-market logistics clients in APAC",
    "why_it_matters": "XYZ Robotics just announced expansion into APAC logistics automation and no one is offering bundled analytics + robotics to mid-size firms.",
    "recommended_action": [
      "Reach out to XYZ Robotics for co-sell pilot",
      "Create a joint outbound pitch targeting Australian logistics providers",
      "Build positioning deck around 'operational efficiency + AI analytics'"
    ],
    "impact": "high",
    "urgency": "now",
    "source_article": "XYZ Robotics expands AI-driven warehouse automation into APAC",
    "source_url": "https://example.com/article-link"
  }}
]

Your response MUST be ONLY pure JSON following that structure.
If you cannot infer any opportunities from the articles, return [].
"""

    try:
        raw = gpt.load_model(
            prompt,
            max_tokens=3000,      # more than enough for ~10-15 opps
            temperature=0.35,     # keep it focused / businessy
            stream=False,
        )

        cleaned = raw.strip()

        # Handle cases where model wraps JSON in ```json ...```
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        result = json.loads(cleaned)

        # Sanity check
        if not isinstance(result, list):
            raise ValueError(f"Expected a list, got {type(result)}")

        # Light post-clean to guarantee keys always exist
        normalized = []
        for item in result:
            normalized.append({
                "opportunity":        item.get("opportunity", "").strip(),
                "why_it_matters":     item.get("why_it_matters", "").strip(),
                "recommended_action": item.get("recommended_action", []),
                "impact":             item.get("impact", "medium"),
                "urgency":            item.get("urgency", "soon"),
                "source_article":     item.get("source_article", "").strip(),
                "source_url":         item.get("source_url", "").strip(),
            })
        return normalized

    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nResponse was:\n{raw}")
    except Exception as e:
        raise RuntimeError(f"Error generating opportunities: {e}")
