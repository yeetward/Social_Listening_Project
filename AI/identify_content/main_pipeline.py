"""
Main Content Distribution Pipeline
=================================

This is the main pipeline that takes an article ID, fetches data from MongoDB,
and provides personalized recommendations with actionable opportunities.
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import our services
from mongo_service import MongoDBService
from user_service import UserService
from enhanced_llm_scorer import EnhancedLLMScorer
from feature_extraction import feature_extraction
from rule_based_scoring import rule_based_scores

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('content_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContentDistributionPipeline:
    """
    Main pipeline for content distribution analysis and recommendations
    """
    
    def __init__(self, mongo_uri: str = None, db_name: str = None, openai_api_key: str = None):
        """
        Initialize the pipeline
        
        Args:
            mongo_uri: MongoDB connection URI
            db_name: Database name
            openai_api_key: OpenAI API key for LLM features
        """
        self.mongo_service = MongoDBService(mongo_uri, db_name)
        self.user_service = UserService(self.mongo_service)
        self.llm_scorer = EnhancedLLMScorer(openai_api_key)
        
        logger.info("Content Distribution Pipeline initialized")
    
    def process_article_by_id(self, 
                            article_id: str, 
                            user_id: str, 
                            use_llm: bool = True,
                            save_results: bool = True) -> Dict[str, Any]:
        """
        Process a single article by ID and provide personalized recommendations
        
        Args:
            article_id: Article ObjectId as string
            user_id: User ObjectId as string
            use_llm: Whether to use LLM recommendations
            save_results: Whether to save results to database
            
        Returns:
            Complete processing results
        """
        try:
            logger.info(f"Processing article {article_id} for user {user_id}")
            
            # Step 1: Fetch article from MongoDB
            article = self.mongo_service.get_article_by_id(article_id)
            if not article:
                return {
                    "success": False,
                    "error": f"Article {article_id} not found",
                    "article_id": article_id,
                    "user_id": user_id
                }
            
            # Step 2: Get user context
            user_context = self.user_service.get_user_context(user_id)
            
            # Step 3: Extract features
            features = feature_extraction(article)
            logger.info(f"Extracted {len(features)} features from article")
            
            # Step 4: Generate rule-based scores
            rule_scores = rule_based_scores(features)
            logger.info("Generated rule-based scores")
            
            # Step 5: Generate LLM recommendations (if enabled)
            llm_recommendations = []
            if use_llm:
                try:
                    llm_recommendations = self.llm_scorer.recommend_distribution_channels(
                        features, article, user_context
                    )
                    logger.info(f"Generated {len(llm_recommendations)} LLM recommendations")
                except Exception as e:
                    logger.warning(f"LLM recommendations failed: {e}")
                    llm_recommendations = []
            
            # Step 6: Personalize recommendations
            personalized_recommendations = self.user_service.personalize_recommendations(
                llm_recommendations, user_context
            )
            
            # Step 7: Generate opportunities
            opportunities = self.user_service.generate_opportunities(
                article, personalized_recommendations, user_context
            )
            
            # Step 8: Generate additional content opportunities
            content_opportunities = []
            if use_llm:
                try:
                    content_opportunities = self.llm_scorer.generate_content_opportunities(
                        article, user_context
                    )
                except Exception as e:
                    logger.warning(f"Content opportunities generation failed: {e}")
            
            # Step 9: Analyze engagement potential
            engagement_analysis = {}
            if use_llm:
                try:
                    engagement_analysis = self.llm_scorer.analyze_engagement_potential(
                        article, user_context
                    )
                except Exception as e:
                    logger.warning(f"Engagement analysis failed: {e}")
            
            # Step 10: Compile results
            results = {
                "success": True,
                "article_id": article_id,
                "user_id": user_id,
                "processed_at": datetime.utcnow().isoformat(),
                "article": {
                    "title": article.get("title", ""),
                    "source": article.get("source", ""),
                    "published_at": article.get("published_at", ""),
                    "engagement": article.get("engagement", {})
                },
                "user_context": {
                    "user_name": user_context.get("user_data", {}).get("name", "Unknown"),
                    "role": user_context.get("preferences", {}).get("role", "marketer"),
                    "industry": user_context.get("preferences", {}).get("industry", "general"),
                    "personalization_score": user_context.get("personalization_score", 0.0)
                },
                "features": features,
                "rule_based_scores": rule_scores,
                "llm_recommendations": llm_recommendations,
                "personalized_recommendations": personalized_recommendations,
                "opportunities": opportunities,
                "content_opportunities": content_opportunities,
                "engagement_analysis": engagement_analysis,
                "summary": self._generate_summary(article, personalized_recommendations, opportunities)
            }
            
            # Step 11: Save results (if requested)
            if save_results:
                saved_id = self.mongo_service.save_recommendation(results)
                if saved_id:
                    results["recommendation_id"] = saved_id
                    logger.info(f"Results saved with ID: {saved_id}")
            
            logger.info(f"Successfully processed article {article_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error processing article {article_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "article_id": article_id,
                "user_id": user_id
            }
    
    def process_multiple_articles(self, 
                                article_ids: List[str], 
                                user_id: str, 
                                use_llm: bool = True,
                                save_results: bool = True) -> Dict[str, Any]:
        """
        Process multiple articles for a user
        
        Args:
            article_ids: List of article ObjectIds as strings
            user_id: User ObjectId as string
            use_llm: Whether to use LLM recommendations
            save_results: Whether to save results to database
            
        Returns:
            Batch processing results
        """
        logger.info(f"Processing {len(article_ids)} articles for user {user_id}")
        
        results = []
        successful = 0
        failed = 0
        
        for i, article_id in enumerate(article_ids):
            logger.info(f"Processing article {i+1}/{len(article_ids)}: {article_id}")
            
            result = self.process_article_by_id(article_id, user_id, use_llm, save_results)
            results.append(result)
            
            if result.get("success", False):
                successful += 1
            else:
                failed += 1
        
        # Generate batch summary
        batch_summary = {
            "total_articles": len(article_ids),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(article_ids) if article_ids else 0,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        return {
            "batch_summary": batch_summary,
            "results": results
        }
    
    def get_user_dashboard(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get a dashboard view for a user with recent recommendations and opportunities
        
        Args:
            user_id: User ObjectId as string
            limit: Maximum number of recent recommendations to fetch
            
        Returns:
            Dashboard data
        """
        try:
            # Get user context
            user_context = self.user_service.get_user_context(user_id)
            
            # Get recent articles
            recent_articles = self.mongo_service.get_recent_articles(limit=limit)
            
            # Get user's recent recommendations (if available)
            # This would require a recommendations collection with user tracking
            recent_recommendations = []
            
            dashboard = {
                "user_id": user_id,
                "user_context": user_context,
                "recent_articles": recent_articles,
                "recent_recommendations": recent_recommendations,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Generated dashboard for user {user_id}")
            return dashboard
            
        except Exception as e:
            logger.error(f"Error generating dashboard for user {user_id}: {e}")
            return {"error": str(e), "user_id": user_id}
    
    def _generate_summary(self, 
                         article: Dict[str, Any], 
                         recommendations: List[Dict[str, Any]], 
                         opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of the processing results"""
        
        # Top recommendations
        top_recommendations = sorted(recommendations, key=lambda x: x.get("score", 0), reverse=True)[:3]
        
        # High-priority opportunities
        high_priority_opportunities = [opp for opp in opportunities if opp.get("priority", 0) >= 0.7]
        
        # Channel distribution
        channel_counts = {}
        for rec in recommendations:
            channel = rec.get("channel", "unknown")
            channel_counts[channel] = channel_counts.get(channel, 0) + 1
        
        return {
            "top_recommendations": [
                {
                    "channel": rec.get("channel", ""),
                    "score": rec.get("score", 0),
                    "reason": rec.get("reason", "")
                }
                for rec in top_recommendations
            ],
            "high_priority_opportunities": len(high_priority_opportunities),
            "total_opportunities": len(opportunities),
            "channel_distribution": channel_counts,
            "article_title": article.get("title", ""),
            "processing_completed": True
        }
    
    def close(self):
        """Close database connections"""
        self.mongo_service.close()
        logger.info("Pipeline connections closed")


def main():
    """
    Main function for command-line usage
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Content Distribution Pipeline")
    parser.add_argument("--article-id", required=True, help="Article ID to process")
    parser.add_argument("--user-id", required=True, help="User ID for personalization")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM recommendations")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to database")
    parser.add_argument("--output", help="Output file path (optional)")
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = ContentDistributionPipeline()
    
    try:
        # Process article
        result = pipeline.process_article_by_id(
            article_id=args.article_id,
            user_id=args.user_id,
            use_llm=not args.no_llm,
            save_results=not args.no_save
        )
        
        # Print results
        if result.get("success"):
            print("\n" + "="*60)
            print("CONTENT DISTRIBUTION ANALYSIS")
            print("="*60)
            print(f"Article: {result['article']['title']}")
            print(f"User: {result['user_context']['user_name']} ({result['user_context']['role']})")
            print(f"Industry: {result['user_context']['industry']}")
            print(f"Personalization Score: {result['user_context']['personalization_score']:.2f}")
            
            print(f"\nTop Recommendations:")
            for i, rec in enumerate(result['summary']['top_recommendations'], 1):
                print(f"  {i}. {rec['channel']}: {rec['score']:.2f}")
                print(f"     {rec['reason']}")
            
            print(f"\nOpportunities: {result['summary']['total_opportunities']} total, {result['summary']['high_priority_opportunities']} high priority")
            
            if result.get('recommendation_id'):
                print(f"\nResults saved with ID: {result['recommendation_id']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to: {args.output}")
    
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
