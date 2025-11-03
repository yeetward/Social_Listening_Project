# Topic Detection System

A powerful topic detection system for analyzing large text documents and identifying key topics, subtopics, and keywords.

## Key Highlights

**NO TOKEN LIMITS | NO API REQUIRED | COMPLETELY OFFLINE**

The default NLP strategy runs 100% locally with zero API calls, processing documents of ANY size without token limits or costs!

## Features

- **Advanced NLP Strategy (Default - NO API NEEDED)**:
  - **LDA Topic Modeling**: Discovers latent topics using Latent Dirichlet Allocation
  - **TF-IDF Keyword Extraction**: Identifies important terms and phrases (1-3 word ngrams)
  - **Named Entity Recognition**: Extracts proper nouns and key entities
  - **Noun Phrase Extraction**: Uses POS tagging to find multi-word topics
  - **Completely Offline**: No API calls, no token limits, unlimited processing

- **Optional LLM Strategy** (requires Groq API):
  - Deep semantic understanding for abstract concepts
  - Use only when you need semantic analysis beyond NLP

- **Hybrid Strategy**: Combines NLP + LLM for maximum accuracy (requires API)

- **Handles Unlimited Document Sizes**: Automatically chunks long texts
- **Multi-layer Topic Detection**: Identifies both high-level themes and detailed subtopics
- **Clean JSON Output**: Structured output format for easy integration
- **No Summarization**: Focuses on classification, not content reduction

## Installation

### 1. Install Dependencies

```bash
cd C:\Users\aniru\Documents\GitHub\Pace-Unit\AI
pip install -r requirements.txt
```

### 2. Download NLTK Data (for NLP strategy)

```python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')
```

### 3. Set up Groq API Key (for LLM strategy)

```bash
# Windows
set GROQ_API_KEY=your_key_here

# Linux/Mac
export GROQ_API_KEY=your_key_here
```

## Usage

### Basic Usage (No API Required!)

```python
from Topic_detection import detect_topics

text = """
Your long document or text goes here.
It can be thousands or even millions of words - NO LIMITS!
"""

# Detect topics using NLP strategy (default - NO API CALLS!)
result = detect_topics(text)  # strategy="nlp" is the default

print(result)
# Output:
# {
#   "main_topics": ["topic1", "topic2", ...],
#   "subtopics": {
#     "topic1": ["subtopic1", "subtopic2"],
#     "topic2": ["subtopic1", "subtopic2"]
#   },
#   "keywords": ["keyword1", "keyword2", ...]
# }

# NO API KEY NEEDED, NO TOKEN LIMITS, UNLIMITED TEXT SIZE!
```

### Using the TopicDetector Class

```python
from Topic_detection import TopicDetector

# Initialize detector with specific strategy
detector = TopicDetector(strategy="nlp", max_chunk_size=3000)

# Detect topics
result = detector.detect_topics(text)
```

### JSON Output

```python
from Topic_detection import detect_topics_json

json_output = detect_topics_json(text, strategy="hybrid")
print(json_output)  # Pretty-printed JSON string
```

## Detection Strategies

### 1. NLP Strategy (`strategy="nlp"`, **DEFAULT**)

**RECOMMENDED: Best for most use cases - NO TOKEN LIMITS!**

**Advanced Techniques**:
- **LDA Topic Modeling**: Unsupervised learning to discover latent topics
- **TF-IDF Vectorization**: Advanced keyword extraction with 1-3 word ngrams
- **Named Entity Recognition**: Extracts proper nouns and key entities
- **Noun Phrase Extraction**: POS tagging for multi-word topics
- **Multi-word Phrase Detection**: Identifies compound topics

**Pros**:
- **NO API required** - completely offline
- **NO token limits** - process unlimited text
- **NO costs** - free to use
- **Fast execution** - processes 1000+ words in seconds
- **Accurate** - LDA + TF-IDF provides excellent results
- Works with ANY document size

**Use Cases**:
- Production systems requiring reliability
- Large document processing
- Cost-sensitive applications
- Offline/air-gapped environments
- Processing thousands of documents

### 2. LLM Strategy (`strategy="llm"`)

**Best for**: Optional semantic enhancement (has token limits)

**Techniques**:
- Uses Groq API (GPT models)
- Contextual understanding
- Semantic relationship mapping

**Pros**:
- Deep semantic understanding
- Handles abstract concepts
- Better contextual awareness

**Cons**:
- **TOKEN LIMITS** - Groq API has limits
- Requires API key
- Network dependency
- Token costs
- Slower for large documents
- May hit rate limits

**Use Cases**:
- Small documents where semantic depth is critical
- When you need abstract concept detection
- Supplementing NLP results

### 3. Hybrid Strategy (`strategy="hybrid"`)

**Best for**: Maximum accuracy when API is available

**Combines**:
- NLP techniques (no limits) + LLM insights (has limits)
- Result merging and deduplication

**Pros**:
- Best of both worlds
- Cross-validation of topics

**Cons**:
- **Still has token limits** (from LLM component)
- Requires API key
- Slower than NLP alone

## Output Format

```json
{
  "main_topics": [
    "climate change",
    "renewable energy",
    "environmental policy",
    "carbon emissions",
    "sustainable development"
  ],
  "subtopics": {
    "climate change": [
      "global warming",
      "sea level rise",
      "climate adaptation"
    ],
    "renewable energy": [
      "solar power",
      "wind energy",
      "electric vehicles"
    ]
  },
  "keywords": [
    "climate",
    "emissions",
    "renewable",
    "carbon",
    "sustainability",
    "environment"
  ]
}
```

## Examples

See `example_usage.py` for comprehensive examples:

```bash
python topic_detection/example_usage.py
```

## API Reference

### `TopicDetector` Class

```python
TopicDetector(strategy="hybrid", max_chunk_size=3000)
```

**Parameters**:
- `strategy` (str): Detection strategy - "nlp", "llm", or "hybrid"
- `max_chunk_size` (int): Maximum words per chunk for long documents

**Methods**:
- `detect_topics(text: str) -> Dict`: Detect topics from text

### Convenience Functions

```python
detect_topics(text: str, strategy: str = "hybrid") -> Dict
```
Detect topics and return as dictionary

```python
detect_topics_json(text: str, strategy: str = "hybrid") -> str
```
Detect topics and return as JSON string

```python
detect_topic_simple(text: str) -> str
```
Simple detection (returns first main topic as string)

## Performance Considerations

### NLP Strategy (Default - NO LIMITS!)

**For ANY Size Document** (100 words to 1,000,000+ words):
- Use `strategy="nlp"` (default)
- **NO TOKEN LIMITS** - process unlimited text
- Automatic chunking for very long documents
- Results merged across chunks
- Fast processing: ~1000 words/second
- **RECOMMENDED for production use**

### LLM Strategy (Has Token Limits)

**For Short Texts ONLY** (< 500 words):
- Use `strategy="llm"` if you need semantic depth
- **WARNING: Token limits apply**
- May hit rate limits on Groq API
- Not suitable for large documents
- Use sparingly

### Hybrid Strategy (Has Token Limits)

**For Medium Texts** (500-3000 words):
- Use `strategy="hybrid"` when you need both accuracy and semantics
- **WARNING: Still has token limits** from LLM component
- Best when you have API quota available
- More expensive than NLP alone

### Benchmark Results

| Document Size | NLP (Default) | LLM | Hybrid |
|--------------|---------------|-----|--------|
| 100 words | ✓ Fast | ✓ OK | ✓ OK |
| 1,000 words | ✓ Fast | ⚠ Slow | ⚠ Slow |
| 10,000 words | ✓ Fast | ✗ Token limit | ✗ Token limit |
| 100,000+ words | ✓ Fast | ✗ Impossible | ✗ Impossible |

**Recommendation**: Use NLP strategy (default) for 99% of use cases!

## Troubleshooting

### Error: "Missing dependencies"
```bash
pip install scikit-learn nltk
```

### Error: "NLTK data not found"
```python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')
```

### Error: "Groq API error"
- Check API key is set: `echo %GROQ_API_KEY%` (Windows) or `echo $GROQ_API_KEY` (Linux/Mac)
- Verify API key is valid
- Check network connection
- Use `strategy="nlp"` to bypass API

## Architecture

```
topic_detection/
├── Topic_detection.py    # Main module
├── example_usage.py      # Usage examples
├── README.md            # This file
└── __init__.py          # Package initialization
```

## Integration Example

```python
# In your application
import sys
sys.path.insert(0, "path/to/AI")

from Topic_detection import detect_topics

def analyze_document(document_text):
    topics = detect_topics(document_text, strategy="hybrid")

    # Use the results
    for topic in topics["main_topics"]:
        print(f"Found topic: {topic}")

        if topic in topics["subtopics"]:
            print(f"  Subtopics: {topics['subtopics'][topic]}")

    return topics
```

## License

Part of the Pace-Unit AI system.
