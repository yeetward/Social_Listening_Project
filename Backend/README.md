# Steps for others to run your backend Django project:

1. Clone your GitHub repo:
   git clone <your-repo-url>
   cd <your-project-folder>

2. (Optional but recommended) Create a virtual environment:
    ### on Mac/Linux
    python -m venv venv
    source .venv/bin/activate  

    ### on Windows
    python -m venv venv
    .\.venv\Scripts\activate

3. Install dependencies:
    pip install -r requirements.txt

    We use django-cors-headers. If you see ModuleNotFoundError: corsheaders, run:
    pip install django-cors-headers

4. Run migrations to create the database
This will generate a fresh db.sqlite3 based on your models: 
    python manage.py makemigrations
    python manage.py migrate

5. (Optional) Create a superuser
For logging into Django admin:
    python manage.py createsuperuser

6.  Seed known sources (nice names/keys for admin)
    Run once per environment (e.g., on teammates’ machines, staging, prod). Safe to re-run; it won’t duplicate:
    python manage.py seed_sources

7. Environment variable (The Guardian)
   Set your Guardian API key in the shell before running:
    ### macOS/Linux:
    export GUARDIAN_API_KEY=61c6baaf-f156-4fd7-8b94-005642818a11

    ### Windows PowerShell:
    $env:GUARDIAN_API_KEY="61c6baaf-f156-4fd7-8b94-005642818a11"

8. Run the development server
    python manage.py runserver

9. Open browser to:
    Health check: http://127.0.0.1:8000/api/health
    Admin UI: http://127.0.0.1:8000/admin/  (login with your superuser)
---

# Fetching data from data sources

1. Open 2 terminals

2. Run the following in each terminals:

Terminal 1: 
- cd Backend (Backend directory)
- source .venv/bin/activate        #on Mac/Linus     venv\Scripts\activate #on Windows.  (Activate virtual environment)
- python manage.py runserver (Start server)


 Terminal 2:
- cd Backend (Backend directory)
- source .venv/bin/activate        #on Mac/Linus     venv\Scripts\activate #on Windows.  (Activate virtual environment)
- Use cURL to test API endpoints (cURL examples below)

3. To verify the server is running, open http://127.0.0.1:8000/api/health in your browser for sanity check.


# Examples cURL:
### Subject only
curl -X POST http://127.0.0.1:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"subject":"AI","day":30}' | jq .

### With location filter (may reduce results)
curl -X POST http://127.0.0.1:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"subject":"AI","location":"Sydney","day":30}' | jq .

### With industry filter
curl -X POST http://127.0.0.1:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"subject":"solar","industry":"energy","day":30}' | jq .
