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

# APIs
GUARDIAN_API_KEY=<your-guardian-key>
REDDIT_CLIENT_ID=<your-reddit-client-id>
REDDIT_CLIENT_SECRET=<your-reddit-client-secret>
REDDIT_USER_AGENT="PACE Discovery Bot"

# Groq (AI)
GROQ_API_KEY=<your-groq-api-key>
GROQ_MODEL_ID=openai/gpt-oss-20b
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
  "_id": ObjectId("671970009af52b4e9b0e0c9d"),
  "url": "https://techcrunch.com/ai-startups/",
  "title": "AI Startups Are Transforming Healthcare",
  "text": "This article discusses how new AI-driven startups are improving diagnostics and treatment speeds.",
  "source": "TechCrunch",
  "published_ts": 1730000000,
  "fetched_at": ISODate("2025-10-22T04:25:00Z"),
  "summary": "AI startups driving innovation in healthcare diagnostics."   
}
```

## 2. ai_results
Stores AI ranked results and summaries for each history entry.

```bash

{
  "_id": ObjectId("671972159af52b4e9b0e0da2"),
  "history_id": ObjectId("67196fd69af52b4e9b0e0c1c"),
  "raw_id": ObjectId("671970009af52b4e9b0e0c9d"),  
  "url": "https://techcrunch.com/ai-startups/",
  "source": "TechCrunch",
  "published_ts": 1730000000,

  // AI-generated fields:
  "ai_title": "AI Startups Are Transforming Healthcare",
  "ai_summary": "This article explores how AI-driven startups are revolutionizing healthcare innovation.",
  "relevance_score": 0.92,
  "rank": 1,

  // Optional analytics fields:
  "tags": ["AI", "Healthcare", "Startups"],
  "influencer_mentions": ["John Doe"],
  "backlinks": ["https://anotherblog.com/post/123"],

  // Queue state
  "status": "done",                 
  "created_at": ISODate("2025-10-22T04:26:00Z"),
  "finished_at": ISODate("2025-10-22T04:30:00Z")
}
```

### 3. history
Tracks user searches and AI progress.

```bash
{
 {
  "_id": ObjectId("67196fd69af52b4e9b0e0c1c"),
  "subject": "AI in Healthcare",
  "location": "",
  "industry": "",
  "sources_used": ["reddit_rss", "techcrunch_rss", "news_rss"],

  "params": {
    "days": 7,
    "fetch_limit": 120,
    "persist_pool_limit": 500
  },

  // AI tracking
  "ai_target": 100,           // expected total
  "ai_count": 87,             // number processed so far
  "ai_ready": true,
  "created_at": ISODate("2025-10-22T04:20:00Z"),
  "finished_at": ISODate("2025-10-22T04:35:00Z")
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
| `/api/trends/`        | GET    | Trends analytics            |
| `/api/topics/top/`    | GET    | Provides trending topics    |
| `/api/debug/mongo/`   | GET    | Debug collection counts     |
| `/api/cards/news/`    | GET    | Provides news feed          |
| `/api/cards/trending/`| GET    | Provides ideas              |



