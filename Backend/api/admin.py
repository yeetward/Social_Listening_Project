# Backend/api/admin.py
from django.contrib import admin
from .models import Source, Post, FetchLog

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "base_url", "created_at")
    search_fields = ("name", "key")

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "published_at", "author", "url", "created_at")
    list_filter = ("source",)
    search_fields = ("title", "text", "author", "url")
    readonly_fields = ("created_at", "updated_at")

@admin.register(FetchLog)
class FetchLogAdmin(admin.ModelAdmin):
    list_display = ("subject", "location", "industry", "days", "limit", "result_count", "created_at")
    search_fields = ("subject", "location", "industry")
    readonly_fields = ("created_at",)
