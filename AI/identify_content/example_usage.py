"""
Example usage of the MongoDB-based Content Distribution Pipeline
"""
from main_pipeline import ContentDistributionPipeline
import json

def example_usage():
    """Example of how to use the new pipeline"""
    
    print("MongoDB-based Content Distribution Pipeline - Example Usage")
    print("=" * 60)
    
    # Initialize the pipeline
    pipeline = ContentDistributionPipeline()
    
    try:
        # Example 1: Process a single article
        print("\n1. Processing Single Article")
        print("-" * 30)
        
        # Note: These IDs would need to exist in your MongoDB
        article_id = "507f1f77bcf86cd799439011"  # Replace with actual article ID
        user_id = "507f1f77bcf86cd799439012"     # Replace with actual user ID
        
        result = pipeline.process_article_by_id(
            article_id=article_id,
            user_id=user_id,
            use_llm=True,  # Enable AI recommendations
            save_results=True
        )
        
        if result.get("success"):
            print(f"✅ Successfully processed article: {result['article']['title']}")
            print(f"   User: {result['user_context']['user_name']}")
            print(f"   Industry: {result['user_context']['industry']}")
            print(f"   Personalization Score: {result['user_context']['personalization_score']:.2f}")
            
            # Show top recommendations
            top_recs = result['summary']['top_recommendations']
            print(f"\n   Top Recommendations:")
            for i, rec in enumerate(top_recs, 1):
                print(f"     {i}. {rec['channel']}: {rec['score']:.2f}")
            
            # Show opportunities
            opps = result['summary']['total_opportunities']
            high_pri = result['summary']['high_priority_opportunities']
            print(f"   Opportunities: {opps} total, {high_pri} high priority")
            
        else:
            print(f"❌ Failed to process article: {result.get('error', 'Unknown error')}")
            print("   This is expected if the article ID doesn't exist in MongoDB")
        
        # Example 2: Process multiple articles
        print("\n2. Processing Multiple Articles")
        print("-" * 30)
        
        article_ids = [
            "507f1f77bcf86cd799439011",
            "507f1f77bcf86cd799439013",
            "507f1f77bcf86cd799439015"
        ]
        
        batch_result = pipeline.process_multiple_articles(
            article_ids=article_ids,
            user_id=user_id,
            use_llm=False,  # Disable LLM for faster processing
            save_results=False
        )
        
        summary = batch_result['batch_summary']
        print(f"✅ Batch processing complete:")
        print(f"   Total articles: {summary['total_articles']}")
        print(f"   Successful: {summary['successful']}")
        print(f"   Failed: {summary['failed']}")
        print(f"   Success rate: {summary['success_rate']:.1%}")
        
        # Example 3: Get user dashboard
        print("\n3. User Dashboard")
        print("-" * 30)
        
        dashboard = pipeline.get_user_dashboard(user_id, limit=5)
        
        if 'error' not in dashboard:
            print(f"✅ Dashboard generated for user {user_id}")
            print(f"   Recent articles: {len(dashboard['recent_articles'])}")
            print(f"   Personalization score: {dashboard['user_context']['personalization_score']:.2f}")
        else:
            print(f"❌ Dashboard generation failed: {dashboard['error']}")
        
        # Example 4: Save results to file
        print("\n4. Saving Results to File")
        print("-" * 30)
        
        if result.get("success"):
            with open("example_results.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print("✅ Results saved to example_results.json")
        
    except Exception as e:
        print(f"❌ Error during example execution: {e}")
    
    finally:
        # Always close the pipeline
        pipeline.close()
        print("\n✅ Pipeline closed")

if __name__ == "__main__":
    example_usage()
