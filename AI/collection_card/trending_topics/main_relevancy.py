from AI.collection_card.trending_topics import analyse_relevancy
from AI.collection_card import company_data_fetch
from AI.collection_card import data_fetch

# def run(company_id: str):
def run(company_id: str,):
    try:
        #Fetch trending topics
        trending_topics = data_fetch.get_company_card(company_id, "trending")
        print("Trending Topics:", trending_topics)
        if not trending_topics:
            raise ValueError("No trending topics retrieved")

        # Build company context
        context = company_data_fetch.get_company_context(company_id)

        # Run AI relevance analysis
        analysis_result = analyse_relevancy.relevancy_rag(context, trending_topics)
 
        return analysis_result

    except Exception as e:
        raise RuntimeError(f"run() failed: {e}")

if __name__ == "__main__":
    company_id = "64b8f3f5e1b2c4a5d6e7f890"  # Example company ID
    result = run(company_id)