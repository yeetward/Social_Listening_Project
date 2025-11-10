from . import reddit_official
from . import reddit_rss
from . import news_gnews
from . import bbc_rss
from . import techcrunch_rss
from . import guardian_api
from . import hackernews_api
from . import newsapi_api

REGISTRY = {
    "Reddit (Official)":  reddit_official.fetch,
    "Reddit (RSS)":       reddit_rss.fetch,
    "Google News":         news_gnews.fetch,      
    "BBC":          bbc_rss.fetch,
    "TechCrunch":   techcrunch_rss.fetch,
    "The Guardian":     guardian_api.fetch,
    "HackerNews":   hackernews_api.fetch,
    "Newsapi":          newsapi_api.fetch,
}