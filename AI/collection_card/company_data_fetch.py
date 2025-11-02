from pymongo import MongoClient
from bson import ObjectId

MONGO_URI = "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["pace_database"]

def get_company_card(company_id: str, card_name: str):
    """Retrieve a specific card (e.g., 'trending', 'newsfeed') for a given company ID."""
    try:
        obj_id = ObjectId(company_id)
    except Exception:
        raise ValueError(f"Invalid company ID format: {company_id}")
    
    company = db.company_profiles.find_one({"_id": obj_id}, {"cards": 1, "_id": 0})
    if not company:
        raise ValueError(f"No company found for ID {company_id}")

    cards = company.get("cards", {})
    card = cards.get(card_name)
    
    if card is None:
        raise ValueError(f"Card '{card_name}' not found for company {company_id}")

    return card 
