# AI/collection_card/main_summaries.py
from __future__ import annotations
import argparse, json, os, sys, time
from typing import Dict, Any

# Reuse your shared fetcher (company-ID centric)
from AI.collection_card.fetch_articles import get_company_articles, get_company_by_id

# Pure-Python extractive summarizer (no LLM)
from .summarize_articles import (
    summarize_articles_to_bullets,
    compact_article_sources,
    per_article_snippets,
)


def log(msg: str, verbose: bool = False) -> None:
    if verbose:
        print(msg, file=sys.stderr)


def run(
    company_id: str,
    *,
    limit: int = 60,
    min_relevance: float = 0.30,
    max_bullets: int = 8,
    max_snippet_chars: int = 220,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Build a cross-article summary (bullets) and per-article snippets for a company, without using an LLM.
    - Pulls AI-enriched articles by company_id
    - Uses TF-IDF centroid + MMR to extract diverse, central sentences
    - Also returns per-article micro-summaries (first sentence, truncated)
    - Returns clean JSON for the frontend (no DB writes)
    """
    try:
        profile = get_company_by_id(company_id)
        if not profile:
            return {
                "company_id": company_id,
                "generated_at_ts": int(time.time()),
                "summary_bullets": [],
                "article_snippets": [],
                "coverage": {"articles_used": 0},
                "sources": [],
                "note": "Company profile not found.",
            }

        articles = get_company_articles(
            company_id,
            limit=limit,
            min_relevance=min_relevance,
        )

        if not articles:
            return {
                "company_id": company_id,
                "company_name": profile.get("name", ""),
                "generated_at_ts": int(time.time()),
                "summary_bullets": [],
                "article_snippets": [],
                "coverage": {"articles_used": 0},
                "sources": [],
                "note": "No recent articles found for this company.",
            }

        bullets = summarize_articles_to_bullets(articles, max_bullets=max_bullets)
        snippets = per_article_snippets(articles, max_chars=max_snippet_chars)
        sources = compact_article_sources(articles)

        # Coverage window
        ts_vals = [int(a.get("published_ts", 0)) for a in articles if a.get("published_ts")]
        coverage = {
            "articles_used": len(articles),
            "time_window": {
                "min_ts": min(ts_vals) if ts_vals else None,
                "max_ts": max(ts_vals) if ts_vals else None,
            }
        }

        return {
            "company_id": company_id,
            "company_name": profile.get("name", ""),
            "generated_at_ts": int(time.time()),
            "summary_bullets": bullets,
            "article_snippets": snippets,   # <-- NEW
            "coverage": coverage,
            "sources": sources,
        }

    except Exception as e:
        raise RuntimeError(f"summaries.run() failed: {e}") from e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize recent articles for a company (no LLM).")
    parser.add_argument("company_id", type=str, help="ObjectId of the company in company_profiles")
    parser.add_argument("--limit", type=int, default=60, help="Max number of recent articles to pull")
    parser.add_argument("--min-relevance", type=float, default=0.30, help="Minimum relevance filter in ai_results")
    parser.add_argument("--max-bullets", type=int, default=8, help="How many summary bullets to return")
    parser.add_argument("--max-snippet-chars", type=int, default=220, help="Max characters per article snippet")
    parser.add_argument("--verbose", action="store_true", help="Debug logs")
    args = parser.parse_args()

    try:
        out = run(
            company_id=args.company_id,
            limit=args.limit,
            min_relevance=args.min_relevance,
            max_bullets=args.max_bullets,
            max_snippet_chars=args.max_snippet_chars,
            verbose=args.verbose,
        )
        print(json.dumps(out, ensure_ascii=False))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
