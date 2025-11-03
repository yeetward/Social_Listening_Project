from AI.collection_card.trending_topics import analyse_relevancy
from AI.collection_card import company_cards
from AI.collection_card import fetch_articles
from datetime import datetime

# def run(company_id: str):
def run(company_id: str,):
    try:
        #Fetch trending topics
        trending_topics = company_cards.get_company_card(company_id, "trending")
        if not trending_topics:
            trending_topics = ["topic1", "topic2", "topic3"]
            # raise ValueError("No trending topics retrieved")

        # Build company context
        context = fetch_articles.get_company_by_id(company_id)

        # Run AI relevance analysis
        analysis_result = analyse_relevancy.relevancy_rag(context, trending_topics)

        # wrap and upsert into MongoDB
        payload = {
            "data": analysis_result,
            "updated_at": datetime.now(),
            "next_refresh_at": None
        }

        success = company_cards.upsert_company_card(company_id, "trending_topics", payload)

        # check for success
        if not success:
            raise RuntimeError("Failed to upsert trending_topics card")

    except Exception as e:
        raise RuntimeError(f"run() failed: {e}")


if __name__ == "__main__":
    company_id = "690531c37c33c037fd2d9bda"  # Example company ID
    result = run(company_id)

