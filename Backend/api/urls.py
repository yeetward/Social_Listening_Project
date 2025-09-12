# Backend/api/urls.py
from django.urls import path
from .views import health, search_posts

urlpatterns = [
    path("health/", health),     # Add trailing slash
    path("search/", search_posts)  # Add trailing slash
]