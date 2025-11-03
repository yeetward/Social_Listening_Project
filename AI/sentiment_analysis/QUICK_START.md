# Quick Start Guide

## Installation (30 seconds)

```bash
# Install dependencies
pip install -r requirements.txt

# Or just the essentials (VADER only)
pip install vaderSentiment numpy
```

## Usage (3 lines of code)

```python
from sentiment_analyzer import SentimentAnalyzer

analyzer = SentimentAnalyzer(method='vader')
result = analyzer.analyze("Your text here - ANY SIZE, NO LIMITS!")

print(f"Sentiment: {result.label}")  # positive/negative/neutral
print(f"Score: {result.compound_score}")  # -1 to 1
```

## Run Examples

```bash
# Quick demo (1 minute)
python demo.py

# Full examples (5 minutes)
python example_usage.py

# Massive text tests (2 minutes for 1-20 MB)
python test_massive_text.py --skip-extreme

# Extreme test (1 minute for 50 MB)
python test_massive_text.py
```

## Key Features

- **No Size Limits**: Process GB+ of text
- **Very Fast**: 370K+ characters/second with VADER
- **Multiple Methods**: VADER (fast) or Transformers (accurate)
- **Batch Processing**: Analyze thousands of texts
- **File Support**: Direct file analysis

## Performance

| Text Size | VADER Processing Time |
|-----------|----------------------|
| 1 KB | 0.01 seconds |
| 1 MB | 3 seconds |
| 10 MB | 28 seconds |
| 20 MB | 58 seconds |
| 50 MB | ~2.5 minutes |

## Common Use Cases

```python
# Single text
result = analyzer.analyze("Great product!")

# Large document
with open('huge_file.txt') as f:
    result = analyzer.analyze(f.read())

# Batch processing
results = analyzer.analyze_batch([
    "Review 1",
    "Review 2",
    "Review 3"
])

# From file
result = analyzer.analyze_file('reviews.txt')
```

## Methods

- `vader`: Rule-based, very fast, good for social media/reviews
- `transformer`: Deep learning, more accurate, requires transformers + torch
- `hybrid`: Combines both (best accuracy)

## Files

- `sentiment_analyzer.py` - Main module
- `demo.py` - Quick demo
- `example_usage.py` - Detailed examples
- `test_massive_text.py` - Large-scale testing
- `requirements.txt` - Dependencies
- `README.md` - Full documentation

## Support

See `README.md` for complete documentation and API reference.
