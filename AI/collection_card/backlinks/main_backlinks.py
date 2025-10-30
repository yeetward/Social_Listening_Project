# # AI/collection_card/main_backlinks.py

# import argparse
# import json
# import os
# import sys
# from pymongo import MongoClient

# from .fetch_backlinks import get_backlinks_for_domain
# from .analyse_backlinks import analyse_backlinks
# from .mongo_backlinks import upsert_backlink_insights, get_top_backlinks

# # --- Mongo Setup ---
# MONGO_URI = os.getenv(
#     "MONGO_URI",
#     "mongodb+srv://AI_Team_Database:46jdJQEZlhoSDagV@cluster0.dqugl74.mongodb.net/pace_database?retryWrites=true&w=majority&appName=Cluster0",
# )
# client = MongoClient(MONGO_URI)
# db = client["pace_database"]


# def get_company_profile(company_name: str):
#     """
#     Pull basic profile for a company from Mongo.
#     Expected shape in Mongo (collection: company_profiles):
#     {
#         name: "Robotic Marketer",
#         domain: "roboticmarketer.com",
#         description: "...",
#         competitors: ["Competitor A", "Competitor B", ...]
#     }
#     """
#     profile = db.company_profiles.find_one({"name": company_name})
#     if not profile:
#         raise ValueError(f"Company '{company_name}' not found in company_profiles")
#     return {
#         "name": profile["name"],
#         "domain": profile.get("domain", ""),
#         "description": profile.get("description", ""),
#         "competitors": profile.get("competitors", []),
#     }


# def log(msg, verbose=False):
#     if verbose:
#         print(msg, file=sys.stderr)


# def run(
#     company_name: str,
#     api_url: str | None = None,
#     api_key: str | None = None,
#     limit: int = 50,
#     no_llm: bool = False,
#     history_id: str | None = None,
#     return_stored: bool = False,
#     verbose: bool = False,
# ):
#     """
#     Programmatic entry point for backlink intelligence.
#     Returns: list[dict] of analysed backlink insights.

#     Args mirror the CLI flags:
#       - company_name: must exist in Mongo 'company_profiles'
#       - api_url/api_key: optional external backlink provider
#       - limit: max backlinks to score / return
#       - no_llm: if True, skip LLM enrichment
#       - history_id: optional ObjectId string for traceability
#       - return_stored: if True, only read cached results from Mongo
#       - verbose: debug logs to stderr
#     """
#     try:
#         if return_stored:
#             log(f"Fetching cached backlink insights for {company_name}", verbose)
#             return get_top_backlinks(company_name, limit=limit)

#         # 1) Company context
#         profile = get_company_profile(company_name)
#         domain = profile.get("domain") or ""
#         if not domain:
#             raise ValueError(
#                 f"Company '{company_name}' has no 'domain' in company_profiles"
#             )
#         log(f"Company: {profile['name']}  Domain: {domain}", verbose)

#         # 2) Fetch backlinks
#         log("Fetching backlinks...", verbose)
#         backlinks_raw = get_backlinks_for_domain(
#             domain=domain,
#             api_url=api_url,
#             api_key=api_key,
#             limit=limit,
#         )
#         log(f"✓ Retrieved {len(backlinks_raw)} backlinks", verbose)

#         if not backlinks_raw:
#             return []

#         # 3) Analyse + (optional) LLM enrich
#         log("Scoring backlinks and enriching with AI...", verbose)
#         analysed = analyse_backlinks(
#             backlinks_raw,
#             company_name=company_name,
#             top_n=limit,
#             with_llm=(not no_llm),
#         )

#         # 4) Persist
#         log("Writing backlink insights to MongoDB...", verbose)
#         upsert_backlink_insights(
#             company_name=company_name,
#             backlinks=analysed,
#             history_id=history_id,
#         )

#         # 5) Return for API layer
#         return analysed

#     except Exception as e:
#         # Let API layer surface 500/4xx with this message
#         raise RuntimeError(f"backlinks.run() failed: {e}") from e


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(
#         description="Collect, score, enrich, and store backlink intelligence for a company."
#     )
#     parser.add_argument(
#         "company_name", type=str, help="Company name (must exist in company_profiles)"
#     )
#     parser.add_argument(
#         "--api-url", type=str, help="External backlinks API endpoint (optional)"
#     )
#     parser.add_argument(
#         "--api-key", type=str, help="API key for backlink provider (optional)"
#     )
#     parser.add_argument("--limit", type=int, default=50, help="Max backlinks to score")
#     parser.add_argument(
#         "--no-llm", action="store_true", help="Disable LLM enrichment step"
#     )
#     parser.add_argument(
#         "--history-id", type=str, help="Optional history ObjectId for traceability"
#     )
#     parser.add_argument("--verbose", action="store_true", help="Debug output to stderr")
#     parser.add_argument(
#         "--return-stored",
#         action="store_true",
#         help="Instead of recomputing, just return what is already in Mongo for this company.",
#     )
#     args = parser.parse_args()

#     try:
#         if args.return_stored:
#             # Just read what we already have in DB for dashboard
#             log(
#                 f" Fetching cached backlink insights for {args.company_name}",
#                 args.verbose,
#             )
#             stored = get_top_backlinks(args.company_name, limit=args.limit)
#             print(json.dumps(stored))
#             sys.exit(0)

#         # 1. load company context
#         profile = get_company_profile(args.company_name)
#         domain = profile["domain"]
#         if not domain:
#             raise ValueError(
#                 f"Company '{args.company_name}' has no 'domain' in company_profiles"
#             )

#         log(f" Company: {profile['name']}  Domain: {domain}", args.verbose)

#         # 2. fetch backlinks
#         log(" Fetching backlinks...", args.verbose)
#         backlinks_raw = get_backlinks_for_domain(
#             domain=domain,
#             api_url=args.api_url,
#             api_key=args.api_key,
#             limit=args.limit,
#         )
#         log(f"✓ Retrieved {len(backlinks_raw)} backlinks", args.verbose)

#         if not backlinks_raw:
#             print("[]")  # return empty JSON list to stdout
#             sys.exit(0)

#         # 3. score + LLM enrich
#         log(" Scoring backlinks and enriching with AI...", args.verbose)
#         analysed = analyse_backlinks(
#             backlinks_raw,
#             company_name=args.company_name,
#             top_n=args.limit,
#             with_llm=(not args.no_llm),
#         )

#         # 4. write to Mongo so frontend can render the 'backlinks' card
#         log(" Writing backlink insights to MongoDB...", args.verbose)
#         upsert_backlink_insights(
#             company_name=args.company_name,
#             backlinks=analysed,
#             history_id=args.history_id,
#         )

#         # 5. return JSON to stdout (for API layer to forward to frontend)
#         print(json.dumps(analysed))

#     except Exception as e:
#         print(f"ERROR: {e}", file=sys.stderr)
#         sys.exit(1)


import argparse
import json
import os
import sys
from pymongo import MongoClient

from .fetch_backlinks import get_backlinks_for_domain
from .analyse_backlinks import analyse_backlinks
from .mongo_backlinks import upsert_backlink_insights, get_top_backlinks
from .company_domain import (
    extract_domain_from_description,
    infer_candidate_domains_from_ai_results,
)

# --- Mongo Setup ---
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://AI_Team_Database:46jdJQEZlhoSDagV@cluster0.dqugl74.mongodb.net/pace_database?retryWrites=true&w=majority&appName=Cluster0",
)
client = MongoClient(MONGO_URI)
db = client["pace_database"]


def get_company_profile(company_name: str) -> dict:
    """
    Pull profile for a company from Mongo (schema-limited):
      { name, created_at, description, competitors }
    """
    profile = db.company_profiles.find_one({"name": company_name})
    if not profile:
        raise ValueError(f"Company '{company_name}' not found in company_profiles")
    return {
        "name": profile["name"],
        "description": profile.get("description", ""),
        "competitors": profile.get("competitors", []),
        "created_at": profile.get("created_at"),
    }


def log(msg, verbose=False):
    if verbose:
        print(msg, file=sys.stderr)


def run(
    company_name: str,
    api_url: str | None = None,
    api_key: str | None = None,
    limit: int = 50,
    no_llm: bool = False,
    history_id: str | None = None,
    return_stored: bool = False,
    verbose: bool = False,
):
    """
    Programmatic entry point for backlink intelligence.
    - No domain stored in DB; we resolve it at runtime (description URL or ai_results inference).
    - Optionally, a one-off domain_override can be provided via CLI/env without changing schema.
    """
    #     try:
    #         if return_stored:
    #             log(f"Fetching cached backlink insights for {company_name}", verbose)
    #             return get_top_backlinks(company_name, limit=limit)

    #         # 1) Company context
    #         profile = get_company_profile(company_name)
    #         description = profile.get("description", "")

    #         # Domain resolution priority:
    #         # a) explicit override (CLI/ENV)
    #         # b) parse from description URL
    #         # c) infer from ai_results URLs
    #         domains: list[str] = []
    #         if domain_override:
    #             domains = [domain_override.lower().strip()]
    #             log(f"Using domain override: {domains[0]}", verbose)
    #         else:
    #             primary = extract_domain_from_description(description)
    #             if primary:
    #                 domains = [primary]
    #                 log(f"Resolved domain from description: {primary}", verbose)
    #             else:
    #                 inferred = infer_candidate_domains_from_ai_results(limit=100)
    #                 if inferred:
    #                     domains = inferred
    #                     log(
    #                         f"No explicit domain. Using inferred candidates: {', '.join(domains[:5])}",
    #                         verbose,
    #                     )

    #         if not domains:
    #             log(
    #                 "No domain resolved/inferred; returning cached backlink insights (if any).",
    #                 verbose,
    #             )
    #             return get_top_backlinks(company_name, limit=limit)

    #         # 2) Fetch backlinks for each candidate domain and merge de-duped
    #         backlinks_raw_all = []
    #         for dom in domains:
    #             log(f"Fetching backlinks for {dom} ...", verbose)
    #             try:
    #                 batch = get_backlinks_for_domain(
    #                     domain=dom, api_url=api_url, api_key=api_key, limit=limit
    #                 )
    #                 backlinks_raw_all.extend(batch or [])
    #             except Exception as fe:
    #                 log(f"! fetch failed for {dom}: {fe}", verbose)

    #         # De-dup by source_url
    #         seen = set()
    #         backlinks_raw = []
    #         for row in backlinks_raw_all:
    #             su = (row.get("source_url") or "").strip().lower()
    #             if su and su not in seen:
    #                 seen.add(su)
    #                 backlinks_raw.append(row)

    #         log(
    #             f"✓ Retrieved {len(backlinks_raw)} unique backlinks across {len(domains)} domain(s)",
    #             verbose,
    #         )
    #         if not backlinks_raw:
    #             return get_top_backlinks(company_name, limit=limit)

    #         # 3) Analyse + (optional) LLM enrich
    #         log("Scoring backlinks and enriching with AI...", verbose)
    #         analysed = analyse_backlinks(
    #             backlinks_raw,
    #             company_name=company_name,
    #             top_n=limit,
    #             with_llm=(not no_llm),
    #         )

    #         # 4) Persist for UI
    #         log("Writing backlink insights to MongoDB...", verbose)
    #         upsert_backlink_insights(
    #             company_name=company_name,
    #             backlinks=analysed,
    #             history_id=history_id,
    #         )

    #         # 5) Return for API layer
    #         return analysed

    #     except Exception as e:
    #         raise RuntimeError(f"backlinks.run() failed: {e}") from e

    # if __name__ == "__main__":
    #     parser = argparse.ArgumentParser(
    #         description="Collect, score, enrich, and store backlink intelligence for a company (no domain field required)."
    #     )
    #     parser.add_argument(
    #         "company_name", type=str, help="Company name (must exist in company_profiles)"
    #     )
    #     parser.add_argument(
    #         "--api-url", type=str, help="External backlinks API endpoint (optional)"
    #     )
    #     parser.add_argument(
    #         "--api-key", type=str, help="API key for backlink provider (optional)"
    #     )
    #     parser.add_argument("--limit", type=int, default=50, help="Max backlinks to score")
    #     parser.add_argument(
    #         "--no-llm", action="store_true", help="Disable LLM enrichment step"
    #     )
    #     parser.add_argument(
    #         "--history-id", type=str, help="Optional history ObjectId for traceability"
    #     )
    #     parser.add_argument("--verbose", action="store_true", help="Debug output to stderr")
    #     parser.add_argument(
    #         "--return-stored",
    #         action="store_true",
    #         help="Return cached results from Mongo instead of recomputing",
    #     )
    #     parser.add_argument(
    #         "--domain-override",
    #         type=str,
    #         help="One-off domain to fetch (does not touch DB schema)",
    #     )
    #     args = parser.parse_args()

    #     try:
    #         results = run(
    #             company_name=args.company_name,
    #             api_url=args.api_url,
    #             api_key=args.api_key,
    #             limit=args.limit,
    #             no_llm=args.no_llm,
    #             history_id=args.history_id,
    #             return_stored=args.return_stored,
    #             verbose=args.verbose,
    #         )
    #         print(json.dumps(results or []))
    #     except Exception as e:
    #         print(f"ERROR: {e}", file=sys.stderr)
    #         sys.exit(1)

    try:
        if return_stored:
            log(f"Reading cached backlinks for {company_name}", verbose)
            return get_top_backlinks(company_name, limit=limit)

        profile = get_company_profile(company_name)
        log(f"Company: {profile['name']}", verbose)

        # Fetch by COMPANY (not domain)
        log("Fetching backlinks (by company)...", verbose)
        raw = get_backlinks_for_company(
            company=profile["name"],
            description=profile["description"],
            api_url=api_url,
            api_key=api_key,
            limit=limit,
        )
        log(f"✓ Retrieved {len(raw)} backlinks", verbose)
        if not raw:
            return []

        log("Scoring & enriching...", verbose)
        analysed = analyse_backlinks(
            raw, company_name=profile["name"], top_n=limit, with_llm=(not no_llm)
        )

        log("Persisting to Mongo...", verbose)
        upsert_backlink_insights(
            company_name=profile["name"], backlinks=analysed, history_id=history_id
        )

        return analysed

    except Exception as e:
        raise RuntimeError(f"backlinks.run() failed: {e}") from e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backlink intelligence by company (no domain field needed)."
    )
    parser.add_argument("company_name", type=str)
    parser.add_argument(
        "--api-url",
        type=str,
        help="Optional provider endpoint that supports company queries",
    )
    parser.add_argument("--api-key", type=str)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--history-id", type=str)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--return-stored", action="store_true")
    args = parser.parse_args()

    try:
        if args.return_stored:
            print(json.dumps(get_top_backlinks(args.company_name, limit=args.limit)))
            sys.exit(0)

        out = run(
            company_name=args.company_name,
            api_url=args.api_url,
            api_key=args.api_key,
            limit=args.limit,
            no_llm=args.no_llm,
            history_id=args.history_id,
            return_stored=False,
            verbose=args.verbose,
        )
        print(json.dumps(out))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
