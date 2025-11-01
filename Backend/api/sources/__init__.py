# Backend/api/sources/__init__.py
from . import reddit_official
from . import reddit_rss
from . import news_gnews
from . import bbc_rss
from . import techcrunch_rss
from . import guardian_api
from . import hackernews_api
from . import newsapi_api

REGISTRY = {
    "reddit_official":  reddit_official.fetch,
    "reddit_rss":       reddit_rss.fetch,
    "news_rss":         news_gnews.fetch,      
    "bbc_rss":          bbc_rss.fetch,
    "techcrunch_rss":   techcrunch_rss.fetch,
    "guardian_api":     guardian_api.fetch,
    "hackernews_api":   hackernews_api.fetch,
    "newsapi":          newsapi_api.fetch,
}