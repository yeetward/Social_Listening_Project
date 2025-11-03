# Quick Start Guide

## NO TOKEN LIMITS - Use NLP Strategy!

The topic detection system now defaults to **NLP strategy** which has:
- **NO API calls**
- **NO token limits**
- **NO costs**
- **Unlimited document size**
- **Fast processing**

## Installation

```bash
pip install scikit-learn nltk
```

## Simplest Usage

```python
from Topic_detection import detect_topics

# Your text - can be ANY size!
text = """
Your document here.
Can be 100 words or 1,000,000 words - NO LIMITS!
"""

# Detect topics (uses NLP by default - NO API!)
result = detect_topics(text)

print(result["main_topics"])
print(result["keywords"])
```

## That's it!

No API keys, no configuration, no token limits. Just install and run!

## How It Works

The enhanced NLP strategy uses:

1. **LDA Topic Modeling** - Discovers latent topics automatically
2. **TF-IDF** - Extracts important keywords and phrases
3. **Named Entity Recognition** - Finds proper nouns and entities
4. **Noun Phrase Extraction** - Identifies multi-word topics
5. **Statistical Analysis** - Combines multiple signals for accuracy

All of this runs **100% locally** with no external API calls!

## Test It

```bash
# Run quick demo
python topic_detection/demo.py

# Run comprehensive long document test
python topic_detection/test_long_document.py

# Run basic tests
python topic_detection/test_basic.py
```

## Advanced Options

```python
from Topic_detection import TopicDetector

# Customize the detector
detector = TopicDetector(
    strategy="nlp",              # Default, no API needed
    use_topic_modeling=True,     # Use LDA (recommended)
    max_chunk_size=3000          # Words per chunk for very long docs
)

result = detector.detect_topics(your_text)
```

## Why NLP Strategy?

| Feature | NLP Strategy | LLM Strategy |
|---------|--------------|--------------|
| API Required | **NO** | YES |
| Token Limits | **NONE** | YES |
| Cost | **FREE** | Paid |
| Speed | **Fast** | Slow |
| Max Size | **Unlimited** | ~3000 words |
| Accuracy | **Excellent** | Very Good |

**Recommendation**: Always use NLP strategy (default) unless you have a specific need for semantic depth on small documents.

## Common Patterns

### Pattern 1: Analyze Multiple Documents

```python
from Topic_detection import detect_topics

documents = [doc1, doc2, doc3, ...]  # Any number of documents!

for doc in documents:
    result = detect_topics(doc)  # No API limits!
    print(f"Topics: {result['main_topics']}")
```

### Pattern 2: Get JSON Output

```python
from Topic_detection import detect_topics_json

json_result = detect_topics_json(text)
# Save to file, send to API, etc.
```

### Pattern 3: Stream Processing

```python
from Topic_detection import TopicDetector

detector = TopicDetector()  # Initialize once

# Process stream of documents
while True:
    doc = get_next_document()
    topics = detector.detect_topics(doc)
    process_topics(topics)
```

## Need Help?

See full documentation in `README.md`

Run examples: `python topic_detection/example_usage.py`
