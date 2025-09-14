# Backend/api/management/commands/seed_sources.py
from django.core.management.base import BaseCommand
from api.models import Source

SEEDS = [
    
    {"key": "reddit_official", "name": "Reddit (Official API)",    "base_url": "https://www.reddit.com/"},

    {"key": "reddit_rss",      "name": "Reddit (RSS)",             "base_url": "https://www.reddit.com/"},
    {"key": "news_rss",        "name": "Google News (RSS)",        "base_url": "https://news.google.com/"},
    {"key": "bbc_rss",         "name": "BBC News (RSS)",           "base_url": "https://www.bbc.co.uk/news"},
    {"key": "techcrunch_rss",  "name": "TechCrunch (RSS)",         "base_url": "https://techcrunch.com/"},
    {"key": "guardian_api",    "name": "The Guardian (API)",       "base_url": "https://content.guardianapis.com/"},
    {"key": "hackernews_api",  "name": "Hacker News (Algolia API)","base_url": "https://hn.algolia.com/"},
]

class Command(BaseCommand):
    help = "Seed default sources"

    def handle(self, *args, **options):
        created = 0
        for s in SEEDS:
            obj, was_created = Source.objects.get_or_create(
                key=s["key"],
                defaults={"name": s["name"], "base_url": s["base_url"]}
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded sources. created={created}"))