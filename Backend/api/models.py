# Backend/api/models.py
from django.db import models
from django.utils import timezone

class Source(models.Model):
    """
    A feed/source descriptor. Seed these for nice names, but we also
    create on-the-fly if an unknown source key shows up.
    """
    key = models.CharField(max_length=100, unique=True)  # e.g., "reddit_rss", "news_rss"
    name = models.CharField(max_length=200)              # e.g., "Reddit (RSS)", "Google News RSS"
    base_url = models.URLField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.key})"


class Post(models.Model):
    """
    A normalized post row representing an item from any source.
    Uniqueness is enforced on URL to avoid duplicates.
    """
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="posts")
    post_id = models.CharField(max_length=255, blank=True, default="")  # upstream id if you want to keep it
    url = models.URLField(unique=True)

    title = models.TextField(blank=True, default="")
    text = models.TextField(blank=True, default="")
    text_html = models.TextField(blank=True, default="")
    author = models.CharField(max_length=255, blank=True, default="")

    # Publish time (normalized to UTC)
    published_at = models.DateTimeField(null=True, blank=True)
    # Keep raw epoch (sec) if you want; helpful for quick sorting without conversion
    published_ts = models.BigIntegerField(null=True, blank=True)

    # engagement shape from your fetchers (nullable JSON)
    engagement = models.JSONField(null=True, blank=True)

    # housekeeping
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["-published_ts"]),
            models.Index(fields=["source", "-published_ts"]),
        ]
        ordering = ["-published_ts", "-id"]

    def __str__(self) -> str:
        return f"[{self.source.key}] {self.title or self.url}"


class FetchLog(models.Model):
    """
    Optional but very useful audit log of searches and how many we persisted.
    """
    subject = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, default="")
    industry = models.CharField(max_length=200, blank=True, default="")
    days = models.IntegerField(default=7)
    limit = models.IntegerField(default=10)

    result_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} (loc='{self.location}' ind='{self.industry}') @ {self.created_at:%Y-%m-%d %H:%M}"
