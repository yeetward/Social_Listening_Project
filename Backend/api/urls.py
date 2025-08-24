from django.urls import path
from .views import health, ProjectCreateView, ProjectDetailView, ProjectListView

urlpatterns = [
    path('health/', health),                
    path('queries/', ProjectCreateView.as_view()),         
    path('queries/list/', ProjectListView.as_view()),       
    path('queries/<int:pk>/', ProjectDetailView.as_view()), 
]
