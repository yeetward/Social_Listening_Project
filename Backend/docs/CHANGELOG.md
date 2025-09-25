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

      Improved MVP search v4 (with hard cap = 10) 
      - Build upstream query from subject + optional location/industry.
      - Fetch Reddit + Google News.
      - Interleave sources, dedupe by URL.
      - Freshness filter: last N days (default 7; override via 'days').
      - Relevance: subject is REQUIRED; title > body; location/industry add boosts.
      - Sort by score desc, then recency desc. No unrelated fallback.
      - Sponsor requirement: return at most 10 results (capped).

      Improved MVP search v5 (with hard cap = 10) + persistence:
      - Build upstream query from subject + optional location/industry.
      - Fetch Reddit + Google News.
      - Interleave sources, dedupe by URL.
      - Freshness filter: last N days (default 7; override via 'days').
      - Relevance: subject is REQUIRED; title > body; location/industry add boosts.
      - Sort by score desc, then recency desc. No unrelated fallback.
      - Sponsor requirement: return at most 10 results (capped).
      - Persist results to DB (upsert by URL) + write FetchLog.

    Improved MVP search v6:
      - Build upstream query from subject + optional location/industry.
      - Fetch Reddit + Google News.
      - Interleave sources, dedupe by URL.
      - Freshness filter: last N days (default 7; override via 'days').
      - Relevance: subject is REQUIRED; title > body; location/industry add boosts.
      - Sort by score desc, then recency desc. No unrelated fallback.
      - Fetch pool size is configurable via 'fetch_limit' (default 30, 10..100).
      - Display cap stays hard at 10 (sponsor requirement) via 'limit' (1..10).
      - Persist results to DB (upsert by URL) + write FetchLog.

      Improved MVP search v7 (Phase-2 sources):
      - Build upstream query from subject + optional location/industry.
      - Fetch from: Reddit RSS, Google News RSS, BBC RSS, TechCrunch RSS, The Guardian API, Hacker News (Algolia).
      - Interleave sources (round-robin), then dedupe by URL.
      - Freshness filter: last N days (default 7; override via 'days').
      - Relevance: subject is REQUIRED; title > body; location/industry add boosts.
      - Sort by score desc, then recency desc. No unrelated fallback.
      - Fetch pool size is configurable via 'fetch_limit' (default 30, 10..100).
      - Display cap stays hard at 10 (sponsor requirement) via 'limit' (1..10).
      - Persist results to DB (upsert by URL) + write FetchLog (save displayed only).

      Improved MVP search v8 (Phase-2 + per-source & test mode):
      - Build upstream query from subject + optional location/industry.
      - Fetch from selected sources (default = all).
      - Interleave, dedupe by URL, freshness filter.
      - Relevance: subject is REQUIRED; title > body; location/industry boosts.
      - Sort by score desc, then recency desc.
      - Fetch pool size via 'fetch_limit' (default 30, 10..100).
      - Display cap HARD at 10 via 'limit' (1..10).
      - Persist (Phase-1 policy: save displayed only) unless persist=false.
      - Adds X-Sources-Used & X-Source-Counts debug headers.
      - NEW: choose sources via 'sources' or 'source' param.
      - NEW: 'persist': false to skip DB writes for testing.