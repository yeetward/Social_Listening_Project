# Change log


1) views.py

    Minimal MVP search:
    - requires "subject" in JSON body
    - optional "limit" (default 10)
    - calls Reddit RSS + Google News RSS fetchers
    - returns a JSON array of normalized post objects

    Minimal MVP search with:
      - required: subject
      - optional: location, industry, limit (default 10)
      - fetch Reddit RSS + Google News RSS
      - clean text
      - interleave sources
      - simple keyword filters for location/industry (case-insensitive)

    MVP search:
      - required: subject
      - optional: location, industry, limit
      - fetch Reddit RSS + Google News RSS
      - interleave sources so one doesn't dominate
      - simple keyword filters for location/industry
      - returns normalized post objects

    Improved MVP search v1:
      - Build upstream query using subject + optional location/industry.
      - Fetch Reddit + Google News with that combined query.
      - Dedupe by URL and sort by recency.
      - Apply local text filters (AND).
      - If filters yield 0, gracefully fall back to unfiltered top items.

    Improved MVP search v2:
      - Build upstream query using subject + optional location/industry.
      - Fetch Reddit + Google News.
      - Interleave sources for variety, then dedupe by URL.
      - Freshness filter (default: last 7 days, adjustable via 'days').
      - Simple relevance score (title gets more weight than body).
      - Local AND-filters remain (location/industry).
      - Fallback to unfiltered if filtered is empty.

          Improved MVP search v3 (strict subject match):
      - Build upstream query from subject + optional location/industry.
      - Fetch Reddit + Google News.
      - Interleave sources, dedupe by URL.
      - Freshness filter: keep items from the last N days (default 7, override via 'days').
      - Relevance score: subject is REQUIRED; title hits weigh more than body; location/industry add boosts.
      - Sort by score desc, then recency desc. No unrelated fallback.