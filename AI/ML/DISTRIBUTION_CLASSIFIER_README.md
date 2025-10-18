# Content Distribution Classifier

A hybrid AI system that recommends the best distribution channels for your articles.

## Overview

The Content Distribution Classifier analyzes articles and recommends optimal distribution channels:
- **Email**: Long-form, personalized, high-value content
- **Newsletter**: Curated, timely, medium-length content
- **Blog**: Evergreen, detailed, comprehensive articles
- **Instagram**: Visual, short, engaging content
- **Social Media**: Breaking news, short updates, viral content

## Features

### Hybrid Approach
- **Rule-Based Analysis** (Fast): Extracts features like word count, engagement, urgency
- **LLM Classification** (Intelligent): Uses transformer models for semantic understanding
- **Weighted Combination**: Balances speed and accuracy

### Key Capabilities
- Single article analysis
- Batch processing for multiple articles
- MongoDB integration for persistence
- Confidence scores and explanations
- Customizable weights and thresholds

## Installation

### Requirements
Already included in your `requirements.txt`:
```
transformers>=4.0.0
torch>=1.7.0
pymongo>=4.15.0
```

### Optional: LLM Models
For LLM-based classification, models are downloaded automatically on first use:
- `facebook/bart-large-mnli` (~1.6GB)

## Quick Start

### 1. Basic Usage

```python
from AI.ML.content_distribution_classifier import analyze_article, get_top_channels

# Your article
article = {
    "title": "Breaking: New AI Technology Announced",
    "body": "Full article text here...",
    "engagement": {"likes": 150, "comments": 45, "shares": 80}
}

# Get recommendations
top_channels = get_top_channels(article, top_n=3, use_llm=False)

for channel, score in top_channels:
    print(f"{channel}: {score:.2f}")
```

### 2. With Explanations

```python
from AI.ML.content_distribution_classifier import explain_recommendation

explanation = explain_recommendation(article, "email")
print(explanation)
```

### 3. Batch Processing

```python
from AI.ML.content_distribution_classifier import analyze_articles_batch

articles = [...]  # List of article dictionaries
results = analyze_articles_batch(articles, use_llm=False)
```

### 4. MongoDB Integration

```python
from AI.Mongo.save_distribution import upsert_distribution_recommendation

# After getting recommendations
upsert_distribution_recommendation(
    article_id=article["_id"],
    recommendations=top_channels
)
```

## Configuration

### Weight Tuning

Adjust the balance between rule-based and LLM-based scoring:

```python
# More rule-based (faster, less nuanced)
top_channels = get_top_channels(
    article,
    rule_weight=0.8,
    llm_weight=0.2,
    use_llm=True
)

# More LLM-based (slower, more intelligent)
top_channels = get_top_channels(
    article,
    rule_weight=0.3,
    llm_weight=0.7,
    use_llm=True
)
```

### Minimum Score Threshold

Filter out low-confidence recommendations:

```python
top_channels = get_top_channels(
    article,
    min_score=0.5  # Only return channels with score >= 0.5
)
```

## Running the Demo

```bash
cd AI/ML
python distribution_demo.py
```

The demo includes:
1. Single article analysis
2. Batch processing
3. Channel grouping
4. MongoDB integration
5. Custom weight configuration
6. Optional LLM classification

## Integration with Existing System

### Option 1: Standalone Script

Create `distribute_articles.py`:

```python
#!/usr/bin/env python3
"""
Analyze articles and recommend distribution channels.
"""
import argparse
from AI.Mongo.mongo_client import get_collection
from AI.ML.content_distribution_classifier import analyze_articles_batch
from AI.Mongo.save_distribution import upsert_distribution_batch

def main():
    parser = argparse.ArgumentParser(description="Recommend distribution channels")
    parser.add_argument("--limit", type=int, default=100, help="Max articles to process")
    parser.add_argument("--use-llm", action="store_true", help="Enable LLM classification")
    args = parser.parse_args()

    # Fetch articles
    posts = get_collection("posts")
    articles = list(posts.find({}).limit(args.limit))

    # Analyze
    results = analyze_articles_batch(articles, use_llm=args.use_llm)

    # Save
    count = upsert_distribution_batch(results)
    print(f"Processed {len(results)} articles, saved {count} recommendations")

if __name__ == "__main__":
    main()
```

Run:
```bash
python distribute_articles.py --limit 50
```

### Option 2: Add to Existing Pipeline

Integrate with your Backend API views:

```python
# Backend/api/views.py
from AI.ML.content_distribution_classifier import get_top_channels

def create_post(request):
    # ... existing code ...

    # Get distribution recommendations
    article = {
        "title": post.title,
        "body": post.content,
        "engagement": {...}
    }

    recommendations = get_top_channels(article, top_n=3, use_llm=False)

    # Store or return recommendations
    # ...
```

## Performance Considerations

### Speed Comparison
- **Rule-based only**: ~1-5ms per article
- **With LLM**: ~500-2000ms per article (first run slower due to model loading)

### Recommendations
1. **Use rule-based for real-time**: Set `use_llm=False` for API endpoints
2. **Use LLM for batch jobs**: Run overnight with `use_llm=True` for better accuracy
3. **Cache results**: Store recommendations in MongoDB and refresh periodically

## API Reference

### Main Functions

#### `analyze_article(article, rule_weight=0.6, llm_weight=0.4, use_llm=True)`
Returns scores for all channels.

**Returns**: `Dict[str, float]` - Channel name to score mapping

#### `get_top_channels(article, top_n=3, use_llm=True, min_score=0.3)`
Returns top N recommended channels.

**Returns**: `List[Tuple[str, float]]` - Sorted list of (channel, score) tuples

#### `explain_recommendation(article, channel)`
Provides human-readable explanation for a channel recommendation.

**Returns**: `str` - Explanation text

#### `analyze_articles_batch(articles, use_llm=True)`
Batch process multiple articles.

**Returns**: `List[Dict[str, Any]]` - List of results with article ID and recommendations

### MongoDB Functions

#### `upsert_distribution_recommendation(article_id, recommendations, metadata=None)`
Save recommendations for a single article.

#### `upsert_distribution_batch(results)`
Save recommendations for multiple articles.

#### `get_distribution_recommendation(article_id)`
Retrieve saved recommendations for an article.

#### `get_articles_by_channel(channel, min_score=0.5, limit=100)`
Find articles recommended for a specific channel.

## MongoDB Schema

### Collection: `distribution_recommendations`

```json
{
  "_id": ObjectId("..."),
  "article_id": "article_001",
  "recommendations": [
    {"channel": "email", "score": 0.85},
    {"channel": "blog", "score": 0.72},
    {"channel": "newsletter", "score": 0.68}
  ],
  "updated_at": ISODate("2025-01-15T10:30:00Z"),
  "metadata": {
    "rule_weight": 0.6,
    "llm_weight": 0.4,
    "model_version": "v1.0"
  }
}
```

## Customization

### Adding New Channels

Edit `content_distribution_classifier.py`:

```python
# Add to CHANNELS list
CHANNELS = ["email", "newsletter", "blog", "instagram", "social_media", "podcast"]

# Add scoring rules in rule_based_scores()
scores["podcast"] = 0.0
if features["has_audio"] or features["word_count"] > 800:
    scores["podcast"] += 0.5
# ...

# Add explanation in explain_recommendation()
elif channel == "podcast":
    if features["has_audio"]:
        explanations.append("Audio content detected")
    # ...
```

### Tuning Rules

Adjust feature weights in `rule_based_scores()` based on your data:

```python
# Make email more sensitive to word count
if features["word_count"] > 300:
    scores["email"] += 0.5  # Increased from 0.3
```

## Troubleshooting

### ImportError: No module named 'transformers'
Install: `pip install transformers torch`

### MongoDB Connection Error
Check `.env` file:
```
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DBNAME=pace_unit
```

### LLM Model Download Fails
- Ensure internet connection
- Model downloads to `~/.cache/huggingface/`
- Requires ~2GB free space

### Low Accuracy
- Increase `llm_weight` to 0.7+
- Set `use_llm=True`
- Tune rules in `rule_based_scores()` for your content

## Examples

See `distribution_demo.py` for comprehensive examples.

## License

Part of the Pace-Unit project.

## Support

For issues or questions, refer to the main project documentation.
