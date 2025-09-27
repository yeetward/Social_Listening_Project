from mongo_client import get_db

db = get_db()
print("DB:", db.name)
print("Collections:", db.list_collection_names())

posts = db["posts"]
print("Count:", posts.estimated_document_count())

for d in posts.find({}, {"_id":1, "title":1, "body":1}).limit(3):
    print(d)
