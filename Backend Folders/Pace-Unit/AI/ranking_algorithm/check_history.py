from pymongo import MongoClient
from bson import ObjectId
import sys, itertools

MONGO_URI = "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
db = MongoClient(MONGO_URI)["pace_database"]

def clauses(h):
    c = [{"history_id": h}]
    try:
        c.append({"history_id": ObjectId(h)})
    except Exception:
        pass
    # common alternate field names people end up using
    alts = ["history", "session_id", "topic_id", "meta.history_id"]
    for f in alts:
        c.append({f: h})
        try:
            c.append({f: ObjectId(h)})
        except Exception:
            pass
    return {"$or": c}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m AI.ranking_algorithm.check_history <history_id>")
        sys.exit(1)
    hid = sys.argv[1]

    cl = clauses(hid)
    raw_cnt = db.raw_insights.count_documents(cl)
    ai_q    = db.ai_results.count_documents({**cl, "status": "queued"})
    ai_d    = db.ai_results.count_documents({**cl, "status": "done"})

    print(f"raw_insights: {raw_cnt}, ai_results queued: {ai_q}, done: {ai_d}")

    # show one sample path so we know which field actually matched
    sample = db.raw_insights.find_one(cl, {"_id":1, "history_id":1, "history":1, "session_id":1, "meta":1})
    if sample:
        print("sample raw_insights doc fields:", {k: sample.get(k) for k in ["_id","history_id","history","session_id","meta"]})
