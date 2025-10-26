"""
Test script to verify imports are working correctly
"""
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_imports():
    """Test all the import statements"""
    
    print("Testing Pace Unit AI Project Imports")
    print("=" * 40)
    
    # Test 1: Basic Python imports
    try:
        from typing import Dict, List, Any, Tuple
        from datetime import datetime, timezone
        from bson import ObjectId
        print("✅ Basic Python imports work")
    except ImportError as e:
        print(f"❌ Basic Python imports failed: {e}")
        return False
    
    # Test 2: MongoDB imports
    try:
        from pymongo import MongoClient, UpdateOne
        print("✅ MongoDB imports work")
    except ImportError as e:
        print(f"❌ MongoDB imports failed: {e}")
        return False
    
    # Test 3: AI package structure
    try:
        import AI
        print("✅ AI package structure works")
    except ImportError as e:
        print(f"❌ AI package structure failed: {e}")
        return False
    
    # Test 4: Individual modules (without heavy dependencies)
    try:
        from AI.ranking_algorithm.engagement_scorer import engagement_score
        print("✅ Engagement scorer imports work")
    except ImportError as e:
        print(f"❌ Engagement scorer failed: {e}")
    
    try:
        from AI.ranking_algorithm.tf_idf_scorer import score_tfidf_simple
        print("✅ TF-IDF scorer imports work")
    except ImportError as e:
        print(f"❌ TF-IDF scorer failed: {e}")
    
    # Test 5: Text processing modules
    try:
        from AI.Text_summarisation.Text_summariser import generate_summary
        print("✅ Text summarizer imports work")
    except ImportError as e:
        print(f"❌ Text summarizer failed: {e}")
    
    try:
        from AI.Topic_detection.Topic_detection import detect_topic_simple
        print("✅ Topic detection imports work")
    except ImportError as e:
        print(f"❌ Topic detection failed: {e}")
    
    # Test 6: MongoDB service
    try:
        from AI.Mongo.mongo_client import get_db
        print("✅ MongoDB client imports work")
    except ImportError as e:
        print(f"❌ MongoDB client failed: {e}")
    
    # Test 7: Content distribution pipeline
    try:
        from AI.identify_content.main_pipeline import ContentDistributionPipeline
        print("✅ Content distribution pipeline imports work")
    except ImportError as e:
        print(f"❌ Content distribution pipeline failed: {e}")
    
    print("\n" + "=" * 40)
    print("Import test completed!")
    return True

if __name__ == "__main__":
    test_imports()
