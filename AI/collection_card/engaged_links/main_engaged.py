from __future__ import annotations
import argparse
import json
from typing import List, Dict, Any
from datetime import datetime, timezone

from AI.collection_card.company_cards import upsert_company_card
from AI.collection_card.engaged_links.fetch_engaged import collect_company_engagement


def run(
    company_id: str,
    *,
    top_n: int = 20,
    limit_docs: int = 400,
    min_relevance: float = 0.10,
    days_back: int = 200,
    persist: bool = True,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    Compute the most engaged links for a company and (optionally) persist to the 'engaged_links' card.
    Returns a list of dicts:
      { url, title, summary, source, published_ts, engagement_score, engagement }
    """
    items, meta = collect_company_engagement(
        company_id,
        limit_docs=limit_docs,
        min_relevance=min_relevance,
        days_back=days_back,
    )

    if verbose:
        cname = meta.get("company_name") or "(unnamed)"
        print(f" Strategy: {meta.get('strategy')}  Company: {cname}")
        print(f" Collected {len(items)} company-related docs with engagement metrics.")

    if not items:
        payload = {
            "items": [],
            "updated_at": datetime.now(timezone.utc),
            "next_refresh_at": None,
            "meta": meta,
        }
        if persist:
            upsert_company_card(company_id, "engaged_links", payload)
        return []

    # Rank: engagement_score desc, then recency desc
    items.sort(
        key=lambda x: (
            float(x.get("engagement_score", 0.0)),
            int(x.get("published_ts", 0)),
        ),
        reverse=True,
    )
    top = items[:top_n]

    if persist:
        payload = {
            "items": top,
            "updated_at": datetime.now(timezone.utc),
            "next_refresh_at": None,
            "meta": meta,
        }
        ok = upsert_company_card(company_id, "engaged_links", payload)
        if verbose:
            print(
                f" Stored {len(top)} engaged links in company card."
                if ok
                else " Warning: failed to save engaged_links."
            )

    return top


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Build 'engaged_links' card with most engaged company-related URLs."
    )
    p.add_argument("company_id", type=str)
    p.add_argument("--top-n", type=int, default=20)
    p.add_argument("--limit-docs", type=int, default=400)
    p.add_argument("--min-relevance", type=float, default=0.10)
    p.add_argument("--days-back", type=int, default=365)
    p.add_argument("--no-persist", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--format",
        choices=["lines", "json"],
        default="lines",
        help="Output only URLs (one-per-line) or as a JSON array.",
    )

    args = p.parse_args()

    out = run(
        args.company_id,
        top_n=args.top_n,
        limit_docs=args.limit_docs,
        min_relevance=args.min_relevance,
        days_back=args.days_back,
        persist=(not args.no_persist),
        verbose=args.verbose,
    )
    items, meta = collect_company_engagement(
        args.company_id,
        limit_docs=args.limit_docs,
        min_relevance=args.min_relevance,
        days_back=args.days_back,
    )

    # If you persist, keep your existing save logic here...
    # (make sure any warnings/errors only print when args.verbose is True)

    # --- OUTPUT: ONLY TOP 10 URLS ---
    urls = [it.get("url", "").strip() for it in items if it.get("url")]

    # Keep only the top 10
    top10 = urls[:10]

    # Print one URL per line
    for u in top10:
        print(u)
