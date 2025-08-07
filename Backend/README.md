✅ Steps for others to run your backend Django project:

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

