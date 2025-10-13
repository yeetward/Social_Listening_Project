from django.contrib import admin
from .models import FetchLog

@admin.register(FetchLog)
class FetchLogAdmin(admin.ModelAdmin):
    list_display = ("subject", "location", "industry", "days", "limit", "result_count", "created_at")
    search_fields = ("subject", "location", "industry")
    readonly_fields =("created_at",)