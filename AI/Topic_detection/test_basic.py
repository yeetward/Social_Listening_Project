"""
Basic test script for topic detection system
Tests core functionality without requiring API keys
"""

import sys
import os

# Add the AI directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
ai_dir = os.path.dirname(current_dir)
sys.path.insert(0, ai_dir)

print("Testing Topic Detection System...")
print("=" * 60)

# Test 1: Import test
print("\n1. Testing imports...")
try:
    from Topic_detection import TopicDetector, detect_topics, detect_topics_json
    print("   [PASS] Imports successful")
except Exception as e:
    print(f"   [FAIL] Import failed: {e}")
    sys.exit(1)

# Test 2: Basic NLP detection (no API required)
print("\n2. Testing NLP-based detection...")
text = """
Machine learning is a subset of artificial intelligence that enables computers
to learn from data. Deep learning uses neural networks with multiple layers.
Natural language processing helps computers understand human language.
Computer vision allows machines to interpret visual information.
"""

try:
    detector = TopicDetector(strategy="nlp")
    result = detector.detect_topics(text)

    print(f"   [PASS] Detection completed")
    print(f"   Main topics found: {len(result.get('main_topics', []))}")
    print(f"   Keywords found: {len(result.get('keywords', []))}")
    print(f"   Topics: {result.get('main_topics', [])[:3]}")

except Exception as e:
    print(f"   [FAIL] NLP detection failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Empty text handling
print("\n3. Testing empty text handling...")
try:
    result = detect_topics("", strategy="nlp")
    assert result["main_topics"] == []
    assert result["keywords"] == []
    print("   [PASS] Empty text handled correctly")
except Exception as e:
    print(f"   [FAIL] Empty text test failed: {e}")

# Test 4: JSON output
print("\n4. Testing JSON output...")
try:
    json_output = detect_topics_json(text, strategy="nlp")
    assert isinstance(json_output, str)
    assert "main_topics" in json_output
    print("   [PASS] JSON output working")
except Exception as e:
    print(f"   [FAIL] JSON output test failed: {e}")

# Test 5: Class-based usage
print("\n5. Testing class-based usage...")
try:
    detector = TopicDetector(strategy="nlp", max_chunk_size=1000)
    result = detector.detect_topics(text)
    assert "main_topics" in result
    assert "subtopics" in result
    assert "keywords" in result
    print("   [PASS] Class-based usage working")
except Exception as e:
    print(f"   [FAIL] Class-based test failed: {e}")

print("\n" + "=" * 60)
print("Basic tests completed!")
print("=" * 60)
