from pymongo import MongoClient
from bson import ObjectId

MONGO_URI = "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["pace_database"]

def get_company_card(company_id, card_name):
    """Fetch a specific card for a given company by its ID."""
    try:
        # --- 2. Fetch company by ID ---
        company = db.find_one({"_id": ObjectId(company_id)})

        if not company:
            print(f"No company found with ID: {company_id}")
            return None

        # --- 3. Retrieve the requested card ---
        cards = company.get("cards", {})
        card_data = cards.get(card_name)

        if card_data is None:
            print(f"Card '{card_name}' not found for this company.")
            return None

        return card_data

    except Exception as e:
        print(f"Error occurred: {e}")
        return None
