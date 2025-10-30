# Backend/api/urls.py
# Backend/api/urls.py
from django.urls import path
from .views import health, search_posts, mongo_status, list_history, get_search_status, get_results
from .views import get_trends
from .views import get_top_topics
from .views import get_company
from .views import card_trends
from .views import card_news


urlpatterns = [
    path("health/", health),
    path("search/", search_posts),
    path("debug/mongo/", mongo_status),

    # --- new endpoints ---
    path("history/", list_history),                # GET list of past searches
    path("search/status/", get_search_status),     # GET AI progress for a history_id
    path("results/", get_results),                 # GET paginated AI results

    # --- for trend analysis ---
    path("trends/", get_trends),

    # for top topic
    path("topics/top/", get_top_topics),

    # for fake company profile
    path("company/", get_company),

    # for cards (company-aware) ---
    path("cards/trending/", card_trends),          # NEW: returns [{topic, relevance}, ...]
    path("cards/news/", card_news),                # NEW: returns {company, count, items:[...]}

]
