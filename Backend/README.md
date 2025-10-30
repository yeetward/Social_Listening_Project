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
Open 2 Terminals. Terminal 1 & 2

# Windows
.venv/Scripts/activate

# macOS / Linux
source .venv/bin/activate
```

## 3.  Install Dependencies
```bash
pip install -r requirements.txt
```


## 4.  Run the Server
```bash
Terminal 1

python manage.py runserver 8001
```

## Quick testing

## `/api/health/`
```bash
Terminal 2

# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/health/" -Method GET |
  ConvertTo-Json -Depth 10

# macOS / Linux
curl -s http://127.0.0.1:8001/api/health/ | jq .
```

## `/api/search/`
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

## `/api/debug/mongo/`
```bash
Terminal 2

# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/debug/mongo/" -Method GET |
  ConvertTo-Json -Depth 10


# macOS / Linux
curl -s http://127.0.0.1:8001/api/debug/mongo/ | jq .
```

## `/api/history/`
```bash
Terminal 2

# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/history/?limit=20" -Method GET |
  ConvertTo-Json -Depth 10

# macOS / Linux
curl -s "http://127.0.0.1:8001/api/history/?limit=20" | jq .
```

## `/api/search/status/`
```bash
Terminal 2

# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/search/status/?history_id=<HISTORY_ID>" -Method GET | ConvertTo-Json -Depth 10

# macOS / Linux
curl -s "http://127.0.0.1:8001/api/search/status/?history_id=<HISTORY_ID>" | jq .
```

## `/api/results/`
```bash
Terminal 2
# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/results/?history_id=<HISTORY_ID>&status=done&page=1&page_size=10" -Method GET | ConvertTo-Json -Depth 10

# macOS / Linux
curl -s "http://127.0.0.1:8001/api/results/?history_id=<HISTORY_ID>&status=done&page=1&page_size=10" | jq .
```

## `/api/trends/`
```bash
Terminal 2
# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/trends/?history_id=<HISTORY_ID>&days=30" -Method GET |
  ConvertTo-Json -Depth 10

# macOS / Linux
curl -s "http://127.0.0.1:8001/api/trends/?history_id=<HISTORY_ID>&days=30" | jq .
```

## `/api/topics/top/`
```bash
Terminal 2
# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/topics/top/?days=30&limit=15" -Method GET |
  ConvertTo-Json -Depth 10

# macOS / Linux
curl -s "http://127.0.0.1:8001/api/topics/top/?days=30&limit=15" | jq .
```

## `/api/company/`
```bash
Terminal 2
# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/company/?name=EcoDrive%20Motors" -Method GET |
  ConvertTo-Json -Depth 10

# macOS / Linux
curl -s "http://127.0.0.1:8001/api/company/?name=EcoDrive%20Motors" | jq .
```

# Cards
## `/api/cards/trending/`
```bash
Terminal 2
# Windows 
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/cards/trending/?company_id=68feebb67c33c037fd2d62f7&threshold=0.5&limit=10&full=1" -Method GET |
  ConvertTo-Json -Depth 10

# macOS / Linux
curl -s "http://127.0.0.1:8001/api/cards/trending/?company_id=68feebb67c33c037fd2d62f7&threshold=0.5&limit=10&full=1" | jq .
```

## `/api/cards/newsfeed/`
```bash
Terminal 2
# Windows 
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/cards/newsfeed/?company_id=68feebb67c33c037fd2d62f7&threshold=0.5&limit=10&full_analysis=1" -Method GET |
  ConvertTo-Json -Depth 10

# macOS / Linux
curl -s "http://127.0.0.1:8001/api/cards/newsfeed/?company_id=68feebb67c33c037fd2d62f7&threshold=0.5&limit=10&full_analysis=1" | jq .
```

## `/api/ai/ideas/`
```bash
Terminal 2
# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/ai/ideas/?company=EcoDrive%20Motors&type=all&limit=10" -Method GET |
  ConvertTo-Json -Depth 10

# macOS / Linux
curl -s "http://127.0.0.1:8001/api/ai/ideas/?company=EcoDrive%20Motors&type=all&limit=10" | jq .
```

## `/api/ai/competitors/`
```bash
Terminal 2
# Windows (PowerShell)
$body = @{
  text       = "We build EV fast chargers for fleets and retail."
  seed_brand = "EcoDrive Motors"
  industry   = @("EV","Charging","Energy")
  location   = @("Australia","New South Wales")
  top_n      = 5
  min_score  = 0.25
  verbose    = $false
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/ai/competitors/" -Method POST `
  -ContentType "application/json" -Body $body |
  ConvertTo-Json -Depth 10

# macOS / Linux
curl -s -X POST "http://127.0.0.1:8001/api/ai/competitors/" \
  -H "Content-Type: application/json" \
  -d '{
    "text":"We build EV fast chargers for fleets and retail.",
    "seed_brand":"EcoDrive Motors",
    "industry":["EV","Charging","Energy"],
    "location":["Australia","New South Wales"],
    "top_n":5,
    "min_score":0.25,
    "verbose":false
  }' | jq .
```

## `/api/ai/backlinks/`
```bash
Terminal 2
# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/ai/backlinks/?company=EcoDrive%20Motors&limit=50&no_llm=0&return_stored=0" -Method GET |
  ConvertTo-Json -Depth 10

# macOS / Linux
curl -s "http://127.0.0.1:8001/api/ai/backlinks/?company=EcoDrive%20Motors&limit=50&no_llm=0&return_stored=0" | jq .
```

## `/api/ai/opportunities/`
```bash
Terminal 2
# Windows
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/ai/opportunities/?company=EcoDrive%20Motors&industry=Electric%20Vehicles&limit=20&min_relevance=0.4" -Method GET |
  ConvertTo-Json -Depth 10

# macOS / Linux
curl -s "http://127.0.0.1:8001/api/ai/opportunities/?company=EcoDrive%20Motors&industry=Electric%20Vehicles&limit=20&min_relevance=0.4" | jq .
```

## Notes
- Ensure your MongoDB cluster and API keys are valid before running the server.

- The default port 8001 can be changed if needed (e.g. runserver 8080).

- All environment variables must be set before launching the Django server.


## API Endpoints

| Endpoint                   | Method | Description |
| --------------------------- | ------ | ------------ |
| `/api/health/`              | GET    | Check if the backend server is running and healthy |
| `/api/search/`              | POST   | Create a new search history, fetch data from all sources, and trigger AI processing |
| `/api/history/`             | GET    | List previously run searches with metadata (subject, date, AI status) |
| `/api/search/status/`       | GET    | Check the AI processing progress for a given `history_id` |
| `/api/results/`             | GET    | Retrieve paginated AI-generated results for a given `history_id` |
| `/api/trends/`              | GET    | Get timeseries trends, top tags, and source breakdown for a `history_id` |
| `/api/topics/top/`          | GET    | Retrieve global trending topics (simple topic list) |
| `/api/debug/mongo/`         | GET    | Show MongoDB collection names and document counts for debugging |
| `/api/company/`             | GET    | Retrieve the latest or specific company profile (name, description, competitors) |
| `/api/cards/trending/`      | GET    | Generate company-aware trending topics using the AI relevancy model |
| `/api/cards/newsfeed/`      | GET    | Generate AI-ranked news feed for a given company  |
| `/api/ai/ideas/`            | GET    | Generate AI-powered idea suggestions based on company insights |
| `/api/ai/competitors/`      | POST   | Identify competitor brands from a given text or context using AI |
| `/api/ai/backlinks/`        | GET    | Retrieve backlinks and sources related to a company       |
| `/api/ai/opportunities/`    | GET    | Generate business opportunities related to a company and industry |


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
