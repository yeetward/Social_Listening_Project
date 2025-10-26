"""
MongoDB Service for Content Distribution Pipeline
================================================

This service handles all MongoDB operations for fetching articles and user data.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class MongoDBService:
    """Service class for MongoDB operations"""
    
    def __init__(self, mongo_uri: str = None, db_name: str = None):
        """
        Initialize MongoDB service
        
        Args:
            mongo_uri: MongoDB connection URI
            db_name: Database name
        """
        self.mongo_uri = mongo_uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.db_name = db_name or os.getenv("MONGODB_DBNAME", "pace_database")
        self._client = None
        self._db = None
    
    def _get_db(self):
        """Get MongoDB database instance"""
        if self._db is None:
            self._client = MongoClient(self.mongo_uri)
            self._db = self._client[self.db_name]
        return self._db
    
    def get_article_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single article by ID
        
        Args:
            article_id: Article ObjectId as string
            
        Returns:
            Article document or None if not found
        """
        try:
            db = self._get_db()
            collection = db["articles"]
            
            # Convert string ID to ObjectId
            if isinstance(article_id, str):
                article_id = ObjectId(article_id)
            
            article = collection.find_one({"_id": article_id})
            
            if article:
                # Convert ObjectId to string for JSON serialization
                article["_id"] = str(article["_id"])
                logger.info(f"Successfully fetched article: {article.get('title', 'Untitled')[:50]}...")
                return article
            else:
                logger.warning(f"Article with ID {article_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching article {article_id}: {e}")
            return None
    
    def get_articles_by_ids(self, article_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple articles by IDs
        
        Args:
            article_ids: List of article ObjectIds as strings
            
        Returns:
            List of article documents
        """
        try:
            db = self._get_db()
            collection = db["articles"]
            
            # Convert string IDs to ObjectIds
            object_ids = [ObjectId(aid) for aid in article_ids if ObjectId.is_valid(aid)]
            
            if not object_ids:
                logger.warning("No valid article IDs provided")
                return []
            
            articles = list(collection.find({"_id": {"$in": object_ids}}))
            
            # Convert ObjectIds to strings
            for article in articles:
                article["_id"] = str(article["_id"])
            
            logger.info(f"Successfully fetched {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching articles: {e}")
            return []
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user data by ID
        
        Args:
            user_id: User ObjectId as string
            
        Returns:
            User document or None if not found
        """
        try:
            db = self._get_db()
            collection = db["users"]
            
            # Convert string ID to ObjectId
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            user = collection.find_one({"_id": user_id})
            
            if user:
                # Convert ObjectId to string for JSON serialization
                user["_id"] = str(user["_id"])
                logger.info(f"Successfully fetched user: {user.get('name', 'Unknown')}")
                return user
            else:
                logger.warning(f"User with ID {user_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None
    
    def get_recent_articles(self, limit: int = 10, source: str = None) -> List[Dict[str, Any]]:
        """
        Fetch recent articles
        
        Args:
            limit: Maximum number of articles to fetch
            source: Filter by source (optional)
            
        Returns:
            List of recent article documents
        """
        try:
            db = self._get_db()
            collection = db["articles"]
            
            query = {}
            if source:
                query["source"] = source
            
            articles = list(collection.find(query)
                          .sort("published_at", -1)
                          .limit(limit))
            
            # Convert ObjectIds to strings
            for article in articles:
                article["_id"] = str(article["_id"])
            
            logger.info(f"Successfully fetched {len(articles)} recent articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching recent articles: {e}")
            return []
    
    def search_articles(self, query: Dict[str, Any], limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search articles with custom query
        
        Args:
            query: MongoDB query dictionary
            limit: Maximum number of articles to return
            
        Returns:
            List of matching article documents
        """
        try:
            db = self._get_db()
            collection = db["articles"]
            
            articles = list(collection.find(query).limit(limit))
            
            # Convert ObjectIds to strings
            for article in articles:
                article["_id"] = str(article["_id"])
            
            logger.info(f"Found {len(articles)} articles matching query")
            return articles
            
        except Exception as e:
            logger.error(f"Error searching articles: {e}")
            return []
    
    def save_recommendation(self, recommendation: Dict[str, Any]) -> Optional[str]:
        """
        Save a recommendation to the database
        
        Args:
            recommendation: Recommendation document to save
            
        Returns:
            ID of saved recommendation or None if failed
        """
        try:
            db = self._get_db()
            collection = db["recommendations"]
            
            recommendation["created_at"] = datetime.utcnow()
            result = collection.insert_one(recommendation)
            
            logger.info(f"Successfully saved recommendation with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error saving recommendation: {e}")
            return None
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user preferences for content distribution
        
        Args:
            user_id: User ObjectId as string
            
        Returns:
            User preferences dictionary
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return self._get_default_preferences()
        
        # Extract preferences from user document
        preferences = {
            "preferred_channels": user.get("preferred_channels", ["email", "newsletter", "blog"]),
            "content_interests": user.get("content_interests", []),
            "industry": user.get("industry", "general"),
            "company_size": user.get("company_size", "small"),
            "role": user.get("role", "marketer"),
            "timezone": user.get("timezone", "UTC"),
            "language": user.get("language", "en"),
            "content_frequency": user.get("content_frequency", "weekly"),
            "engagement_threshold": user.get("engagement_threshold", 0.3),
            "max_content_length": user.get("max_content_length", 1000),
            "min_content_length": user.get("min_content_length", 100),
            "excluded_topics": user.get("excluded_topics", []),
            "included_sources": user.get("included_sources", []),
            "excluded_sources": user.get("excluded_sources", []),
            "urgency_preference": user.get("urgency_preference", "medium"),
            "visual_content_preference": user.get("visual_content_preference", True),
            "personalization_level": user.get("personalization_level", "medium")
        }
        
        return preferences
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences when user data is not available"""
        return {
            "preferred_channels": ["email", "newsletter", "blog"],
            "content_interests": [],
            "industry": "general",
            "company_size": "small",
            "role": "marketer",
            "timezone": "UTC",
            "language": "en",
            "content_frequency": "weekly",
            "engagement_threshold": 0.3,
            "max_content_length": 1000,
            "min_content_length": 100,
            "excluded_topics": [],
            "included_sources": [],
            "excluded_sources": [],
            "urgency_preference": "medium",
            "visual_content_preference": True,
            "personalization_level": "medium"
        }
    
    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
