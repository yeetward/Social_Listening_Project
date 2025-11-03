from AI.collection_card.trending_topics import analyse_relevancy
from AI.collection_card import company_cards
from AI.collection_card import fetch_articles
from AI.collection_card.opportunities import fetch_docs
from datetime import datetime


# def run(company_id: str):
def run(company_id: str,history_id: str):
    try:
        if not company_id:
            raise ValueError("Please enter a valid company_id")
        
        if not history_id:
            raise ValueError("Please enter a valid history_id")

        # Build company context
        context = fetch_articles.get_company_by_id(company_id)

        # Fetch topics from history
        docs = fetch_docs.fetch_articles(history_id)

        print("Fetched Documents:", docs)
        print("Company Context:", context)

        '''

        # Run AI relevance analysis
        analysis_result = analyse_relevancy.relevancy_rag(context, trending_topics)

        print("Analysis Result:", analysis_result)

        # Filter topics with relevance > 0.5
        high_relevance_topics = [
            item["topic"]
            for item in analysis_result
                if isinstance(item, dict) and item.get("relevance", 0) > 0.5
            ]

        
        # wrap and upsert into MongoDB
        payload = {
            "data": high_relevance_topics,
            "updated_at": datetime.now(),
            "next_refresh_at": None
        }

        success = company_cards.upsert_company_card(company_id, "trending_topics", payload)

        # check for success
        if not success:
            raise RuntimeError("Failed to upsert trending_topics card")
        '''
        

    except Exception as e:
        raise RuntimeError(f"run() failed: {e}")

# ----------- CLI for testing --------------------------------------
if __name__ == "__main__":
    company_id = "690531c37c33c037fd2d9bda"  # Example company ID
    history_id = "6900b9d93b7866e2ec8bdc91"  # Example history ID
    result = run(company_id,history_id)

