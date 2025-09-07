# Backend/api/urls.py
from django.urls import path
from .views import (
    health,
    search_posts,
    ProjectCreateView,
    ProjectListView,
    ProjectDetailView,
)

urlpatterns = [
    path("health", health),
    path("search", search_posts),  # MVP endpoint

    # Optional: sample model CRUD
    path("projects", ProjectListView.as_view()),
    path("projects/new", ProjectCreateView.as_view()),
    path("projects/<int:pk>", ProjectDetailView.as_view()),
]
