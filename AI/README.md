# 1) Clone

git clone <https://github.com/khawaja1447/Pace-Unit/tree/main>
cd <repo>

# 2) create and activate a virtual environment

python -m venv .venv

# Windows

.venv/Scripts/activate

# macOS/Linux

source .venv/bin/activate

# 3) Install requirements (CPU-only default)

pip install -r requirements.txt

# 4) call the main function based on your requirements:

## default algos (code defaults to ["sbert"] if we omit --algos)

python -m AI.main "gen ai"

## change the limit

python -m AI.main "gen ai" --limit 500

## pick algorithms

python -m AI.main "gen ai" --algos sbert tfidf engagement

## weighted mix (PowerShell quoting)

python -m AI.main "gen ai" --algos sbert tfidf engagement --weights '{"tfidf":0.35,"sbert":0.45,"engagement":0.20}'

## disable DB writes (preview only)

python -m AI.main "gen ai" --no-persist
