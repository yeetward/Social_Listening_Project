# AI/ranking_algorithm/run_pipeline.py
from AI.ranking_algorithm.seed_ai_results import main as seed_once
from AI.ranking_algorithm.check_history import clauses
from AI.ranking_algorithm.main import run as rank_run
from pymongo import MongoClient
from bson import ObjectId
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = MongoClient(MONGO_URI)["pace_database"]

def run_pipeline(history_id: str, keyword: str):
    # 1) If there are no queued rows for this history, seed them
    hid_clause = clauses(history_id)
    has_queued = db.ai_results.count_documents({**hid_clause, "status":"queued"}) > 0
    if not has_queued:
        seed_once(history_id)  # will create queued items from raw_* using url/raw_id

    # 2) Run ranking + summarization
    return rank_run(history_id, keyword)
