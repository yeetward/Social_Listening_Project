# Backend/api/cleanup_raw_insights.py
from datetime import datetime, timedelta
from bson import ObjectId
from .persist import get_mongo_db

def cleanup_raw_insights(days_threshold=7, dry_run=True):
    """
    Deletes raw_insights docs whose corresponding history entry is ai_ready=true
    and older than <days_threshold> days.
    Set dry_run=False to actually delete.
    """
    db = get_mongo_db()
    cutoff = datetime.utcnow() - timedelta(days=days_threshold)

    # Find processed histories older than the threshold
    ready_histories = list(db.history.find(
        {"ai_ready": True, "created_at": {"$lt": cutoff}},
        {"_id": 1, "subject": 1, "created_at": 1}
    ))

    if not ready_histories:
        print("No eligible histories found for cleanup.")
        return

    print(f"Found {len(ready_histories)} processed histories older than {days_threshold} days.")
    deleted_total = 0

    for h in ready_histories:
        hid = h["_id"]
        count = db.raw_insights.count_documents({"history_id": hid})
        print(f"- {h['subject']} ({h['created_at'].strftime('%Y-%m-%d')}): {count} docs")

        if not dry_run and count > 0:
            res = db.raw_insights.delete_many({"history_id": hid})
            deleted_total += res.deleted_count

    if dry_run:
        print("Dry run mode: no deletions performed. Pass dry_run=False to execute.")
    else:
        print(f"Cleanup complete. Deleted {deleted_total} raw_insights docs.")