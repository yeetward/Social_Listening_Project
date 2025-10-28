from pymongo import MongoClient

MONGO_URI = "mongodb+srv://AI_Team_Database:46jdJQEZlhoSDagV@cluster0.dqugl74.mongodb.net/pace_database?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["pace_database"]

def latest_histories():
    latest_history = list(
        db.history.find({},{"subject":1, "created_at":1})
        .sort("created_at",-1).limit(10)
    )

if __name__ == "__main__":
    latest_histories()