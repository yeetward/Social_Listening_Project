# AI/collection_card/fetch_backlinks.py

from typing import List, Dict, Any
import requests


def get_backlinks_for_domain(
    domain: str,
    api_url: str | None = None,
    api_key: str | None = None,
    limit: int = 100,
    timeout: int = 30,
) -> List[Dict[str, Any]]:
    """
    Fetch backlinks pointing to `domain`.

    Returns a list of dicts like:
    {
        "source_url": "...",
        "source_domain": "...",
        "target_url": "...",
        "anchor_text": "...",
        "dofollow": true,
        "estimated_monthly_clicks": 120,
        "domain_authority": 74
    }

    You can wire this to a live SEO API later. For now we allow:
    - mock/offline data (api_url is None)
    - or GET {api_url}?target=domain with api_key header
    """
    if api_url is None:
        # mock data for now / offline mode
        return [
            {
                "source_url": "https://marketingnews.example.com/ai-marketing-tools-2025",
                "source_domain": "marketingnews.example.com",
                "target_url": f"https://{domain}/product/insights",
                "anchor_text": "AI marketing automation platform",
                "dofollow": True,
                "estimated_monthly_clicks": 140,
                "domain_authority": 78,
            },
            {
                "source_url": "https://randomdirectory.example.org/startups",
                "source_domain": "randomdirectory.example.org",
                "target_url": f"https://{domain}/",
                "anchor_text": f"{domain}",
                "dofollow": False,
                "estimated_monthly_clicks": 2,
                "domain_authority": 12,
            },
            {
                "source_url": "https://competitorx.ai/comparison/robotic-marketer-vs-others",
                "source_domain": "competitorx.ai",
                "target_url": f"https://{domain}/features",
                "anchor_text": "compare us with Robotic Marketer",
                "dofollow": True,
                "estimated_monthly_clicks": 60,
                "domain_authority": 55,
            },
        ]

    # live mode (future)
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    resp = requests.get(
        api_url,
        params={"target": domain, "limit": limit},
        headers=headers,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()

    # We normalize into our expected schema
    normalized: List[Dict[str, Any]] = []
    for row in data.get("backlinks", []):
        normalized.append(
            {
                "source_url": row.get("source_url"),
                "source_domain": row.get("source_domain")
                or row.get("referring_domain"),
                "target_url": row.get("target_url"),
                "anchor_text": row.get("anchor_text") or "",
                "dofollow": bool(row.get("dofollow", True)),
                "estimated_monthly_clicks": row.get("traffic", 0),
                "domain_authority": row.get("domain_authority", 0),
            }
        )
    return normalized


# from typing import List, Dict, Any
# import requests


# def get_backlinks_for_domain(
#     domain: str,
#     api_url: str | None = None,
#     api_key: str | None = None,
#     limit: int = 100,
#     timeout: int = 30,
# ) -> List[Dict[str, Any]]:
#     """
#     Fetch backlinks pointing to `domain`.
#     Returns normalized list:
#     {
#       "source_url": "...",
#       "source_domain": "...",
#       "target_url": "...",
#       "anchor_text": "...",
#       "dofollow": true,
#       "estimated_monthly_clicks": 120,
#       "domain_authority": 74
#     }
#     """
#     if not domain:
#         return []

#     if api_url is None:
#         # Offline/mock mode
#         return [
#             {
#                 "source_url": "https://marketingnews.example.com/ai-marketing-tools-2025",
#                 "source_domain": "marketingnews.example.com",
#                 "target_url": f"https://{domain}/product/insights",
#                 "anchor_text": "AI marketing automation platform",
#                 "dofollow": True,
#                 "estimated_monthly_clicks": 140,
#                 "domain_authority": 78,
#             },
#             {
#                 "source_url": "https://randomdirectory.example.org/startups",
#                 "source_domain": "randomdirectory.example.org",
#                 "target_url": f"https://{domain}/",
#                 "anchor_text": f"{domain}",
#                 "dofollow": False,
#                 "estimated_monthly_clicks": 2,
#                 "domain_authority": 12,
#             },
#             {
#                 "source_url": "https://competitorx.ai/comparison/robotic-marketer-vs-others",
#                 "source_domain": "competitorx.ai",
#                 "target_url": f"https://{domain}/features",
#                 "anchor_text": "compare us with Robotic Marketer",
#                 "dofollow": True,
#                 "estimated_monthly_clicks": 60,
#                 "domain_authority": 55,
#             },
#         ][:limit]

#     headers = {}
#     if api_key:
#         headers["Authorization"] = f"Bearer {api_key}"

#     resp = requests.get(
#         api_url,
#         params={"target": domain, "limit": limit},
#         headers=headers,
#         timeout=timeout,
#     )
#     resp.raise_for_status()
#     data = resp.json()

#     normalized: List[Dict[str, Any]] = []
#     for row in data.get("backlinks", []):
#         normalized.append(
#             {
#                 "source_url": row.get("source_url"),
#                 "source_domain": row.get("source_domain")
#                 or row.get("referring_domain"),
#                 "target_url": row.get("target_url"),
#                 "anchor_text": row.get("anchor_text") or "",
#                 "dofollow": bool(row.get("dofollow", True)),
#                 "estimated_monthly_clicks": row.get("traffic", 0),
#                 "domain_authority": row.get("domain_authority", 0),
#             }
#         )
#     return normalized
