# Backend/api/urls.py
from django.urls import path
from .views import health, search_posts, mongo_status


urlpatterns = [
    path("health/", health),     # Add trailing slash
    path("search/", search_posts),  # Add trailing slash
     path("debug/mongo/", mongo_status)
]