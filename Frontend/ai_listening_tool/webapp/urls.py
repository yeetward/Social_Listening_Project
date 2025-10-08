from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from ai_listening_tool.listening_tool import views as api_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "tool/",
        include(("ai_listening_tool.listening_tool.urls", "listening_tool"),
                namespace="listening_tool"),
    ),
    path("api/search/", api_views.search_api, name="api_search"),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
