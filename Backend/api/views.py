from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from rest_framework import generics
from .models import project
from .serializer import ProjectSerializer  

def health(request):
    return JsonResponse({"status": "ok", "version": "v1"})

class ProjectCreateView(generics.CreateAPIView):
    queryset = project.objects.all()
    serializer_class = ProjectSerializer

class ProjectListView(generics.ListAPIView):
    queryset = project.objects.order_by("-id")
    serializer_class = ProjectSerializer

class ProjectDetailView(generics.RetrieveAPIView):
    queryset = project.objects.all()
    serializer_class = ProjectSerializer
