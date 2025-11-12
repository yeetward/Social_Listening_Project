# Frontend

Django UI for the social-listening project. Renders search, results, and history pages and calls the backend API.

## Requirements
- Python 3.11+
- pip
- Django 5.x

## Setup
```bash
cd Frontend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install "Django>=5.2,<6"
python manage.py migrate
Configure
Edit the frontend config file (e.g. listening_tool/static/ai_listening_tool/js/config.js) and set your API base:

js
Copy code
(function () {
  window.RM_TOOL_CONFIG = {
    API_BASE: "http://127.0.0.1:5000/api", // change to your backend
    timeoutMs: 20000
  };
})();
Run
bash
Copy code
# Use a port that does not clash with your backend
python manage.py runserver 8001
