# Backend/api/urls.py
# Backend/api/urls.py
from django.urls import path
from .views import health, search_posts, mongo_status, list_history, get_search_status, get_results, ai_generate_ideas, ai_competitors, ai_backlinks, ai_opportunities
from .views import get_trends
from .views import get_top_topics
from .views import get_company
from .views import card_trends
from .views import news_feed
from .views import upsert_company
from .views import list_companies

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

    # Company profile
    path("company/", get_company),
    path("company/upsert/", upsert_company),     # POST create/update one profile
    path("companies/", list_companies),          # GET list/search profiles

    # for cards (company-aware) ---
    path("cards/trending/", card_trends),          # NEW: returns [{topic, relevance}, ...]
    path("cards/newsfeed/", news_feed),                # NEW: returns {company, count, items:[...]}
    path("ai/ideas/", ai_generate_ideas),          # for ideas 
    path("ai/competitors/", ai_competitors),
    path("ai/backlinks/", ai_backlinks),
    path("ai/opportunities/", ai_opportunities),

]
