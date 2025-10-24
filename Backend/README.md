# Setup Guide

Follow the steps below to set up and run the **PACE Discovery Bot Backend** locally.

---

## 1.  Clone Repository

```bash
git clone <your-repo-url>
cd Backend
```

## 2.  Create and Activate Virtual Environment

```bash
python -m venv .venv
```

```bash
Terminal 1 & 2

# Windows
venv_backend\Scripts\activate

# macOS / Linux
source venv_backend/bin/activate
```

## 3.  Install Dependencies
```bash
pip install -r requirements.txt
```

## 4.  Configure Environment Variables
Create a .env file in the root directory:

```bash
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/
MONGODB_DBNAME=pace_database
DJANGO_SETTINGS_MODULE=backend.settings
GUARDIAN_API_KEY=<your-guardian-key>
REDDIT_CLIENT_ID=<your-reddit-client-id>
REDDIT_CLIENT_SECRET=<your-reddit-client-secret>
REDDIT_USER_AGENT="PACE Discovery Bot"
```

## 5.  Run the Server
```bash
Terminal 1

python manage.py runserver 8001
```

## 6. Health Check

```bash
Terminal 2

# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/health/" -Method GET

# macOS / Linux
curl http://127.0.0.1:8001/api/health/
```

## Quick testing

```bash
Terminal 2

# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/search/" -Method POST `
-Body '{"subject":"Artificial Intelligence"}' -ContentType "application/json"


# macOS / Linux
curl -X POST http://127.0.0.1:8001/api/search/ \
-H "Content-Type: application/json" \
-d '{"subject":"Artificial Intelligence"}'
```

## Notes
- Ensure your MongoDB cluster and API keys are valid before running the server.

- The default port 8001 can be changed if needed (e.g. runserver 8080).

- All environment variables must be set before launching the Django server.

---

# MongoDB Collections

## 1. raw_insights
Stores raw articles/posts before AI processing.

```bash
{
  "_id": ObjectId,
  "url": "https://example.com/article",
  "source": "reddit_official",
  "title": "AI Revolution",
  "text": "Artificial Intelligence continues to transform marketing...",
  "author": "techguru",
  "published_ts": 1730100000,
  "engagement": { "score": 230, "num_comments": 34 },
  "tags": ["AI", "Marketing"],
  "created_at": ISODate
}
```

## 2. ai_results
Stores AI ranked results and summaries for each history entry.

```bash
{
  "_id": ObjectId,
  "history_id": ObjectId("..."),
  "url": "https://example.com/article",
  "rank": 1,
  "relevance_score": 0.93,
  "ai_title": "AI Reshapes Marketing",
  "ai_summary": "AI is transforming marketing workflows through automation.",
  "tags": ["AI", "Automation"],
  "source": "news_rss",
  "published_ts": 1730100000,
  "created_at": ISODate
}
```

### 3. history
Tracks user searches and AI progress.

```bash
{
  "_id": ObjectId,
  "subject": "Artificial Intelligence",
  "location": "US",
  "industry": "Technology",
  "sources_used": ["reddit_official", "news_rss"],
  "params": { "days": 7, "fetch_limit": 120, "persist_pool_limit": 500 },
  "created_at": ISODate,
  "ai_ready": false,
  "ai_count": 0,
  "ai_target": 100,
  "started_at": null,
  "last_updated": null,
  "finished_at": null
}
```

## MongoDB Indexes
```bash
db.raw_insights.createIndex({ url: 1 }, { unique: true })
db.raw_insights.createIndex({ published_ts: -1 })
db.ai_results.createIndex({ history_id: 1, rank: 1 })
db.history.createIndex({ created_at: -1 })
```

## API Endpoints

| Endpoint              | Method | Description                 |
| --------------------- | ------ | --------------------------- |
| `/api/health/`        | GET    | Check server status         |
| `/api/search/`        | POST   | Create history + fetch data |
| `/api/history/`       | GET    | List previous searches      |
| `/api/search/status/` | GET    | Check AI progress           |
| `/api/results/`       | GET    | Paginated AI results        |
| `/api/debug/mongo/`   | GET    | Debug collection counts     |


