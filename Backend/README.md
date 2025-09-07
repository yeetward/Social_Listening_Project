# Steps for others to run your backend Django project:

1. Clone your GitHub repo
    git clone <your-repo-url>
    cd <your-project-folder>

2. (Optional but recommended) Create a virtual environment
    python -m venv venv
    source venv/bin/activate  # on Mac/Linux
    venv\Scripts\activate     # on Windows

3.Install dependencies
    pip install -r requirements.txt

4. Run migrations to create the database
This will generate a fresh db.sqlite3 based on your models: 
    python manage.py makemigrations
    python manage.py migrate

5. (Optional) Create a superuser
For logging into Django admin:
    python manage.py createsuperuser

6. Run the development server
    python manage.py runserver

7.Open browser to:
    http://127.0.0.1:8000/

---

# Steps to fetch data from data sources

1. Open 2 terminals

2. For each terminal:

### Terminal 1: 
- cd Backend (Backend directory)
- source .venv/bin/activate (venv environment)
- python manage.py runserver (run server)

### Terminal 2:
- cd Backend (Backend directory)
- source .venv/bin/activate (venv environment)
- Send cURL (client url)

http://127.0.0.1:8000/api/health in browser for sanity check


# Examples cURL:
### Subject only
curl -X POST http://127.0.0.1:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"subject":"AI","limit":8}' | jq .

### With location filter (may reduce results!)
curl -X POST http://127.0.0.1:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"subject":"AI","location":"Sydney","limit":8}' | jq .

### With industry filter
curl -X POST http://127.0.0.1:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"subject":"solar","industry":"energy","limit":8}' | jq .
