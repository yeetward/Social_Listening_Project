# Backend/api/urls.py
from django.urls import path
from .views import health, search_posts

urlpatterns = [
    path("health", health),     # -> /api/health
    path("search", search_posts)  # -> /api/search
]