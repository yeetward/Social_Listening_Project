try:
    from transformers import pipeline
except Exception:
    pipeline = None

# Lazily-initialized cached classifier to avoid reloading the model on every call
_CLASSIFIER = None


def _get_classifier(model_name="facebook/bart-large-mnli"):
    """Return a cached zero-shot classification pipeline. Raises RuntimeError if transformers is not available."""
    global _CLASSIFIER
    if pipeline is None:
        raise RuntimeError("transformers is not installed or failed to import. Install 'transformers' to use detect_topic.")
    if _CLASSIFIER is None:
        _CLASSIFIER = pipeline("zero-shot-classification", model=model_name)
    return _CLASSIFIER


def detect_topic(text, candidate_labels=None, model_name="facebook/bart-large-mnli", multi_label=False):
    """Detect the topic of the given text using zero-shot classification.

    Args:
        text (str): The text to classify.
        candidate_labels (list): List of possible topic labels. If None, uses default topics.
        model_name (str): The model to use for classification.
        multi_label (bool): If True, allows multiple topics to be assigned to the text.

    Returns:
        dict: A dictionary containing:
            - 'labels': List of labels sorted by score (highest first)
            - 'scores': List of confidence scores corresponding to each label
            - 'top_topic': The most likely topic
            - 'top_score': The confidence score of the top topic

    Notes:
    - The heavy model is cached after the first call.
    - Default topics cover common categories like technology, sports, politics, etc.
    """
    classifier = _get_classifier(model_name=model_name)

    # Default topic labels if none provided
    if candidate_labels is None:
        candidate_labels = [
            "technology",
            "sports",
            "politics",
            "business",
            "entertainment",
            "science",
            "health",
            "education",
            "environment",
            "travel"
        ]

    # Truncate text if it's too long (similar to summarizer)
    max_input_length = 512  # Tokens, roughly ~400 words
    if len(text.split()) > max_input_length:
        text = " ".join(text.split()[:max_input_length])

    # Perform classification
    result = classifier(text, candidate_labels, multi_label=multi_label)

    return {
        "labels": result["labels"],
        "scores": result["scores"],
        "top_topic": result["labels"][0],
        "top_score": result["scores"][0]
    }


def detect_topic_simple(text, candidate_labels=None, model_name="facebook/bart-large-mnli"):
    """Simplified version that returns just the top topic as a string.

    Args:
        text (str): The text to classify.
        candidate_labels (list): List of possible topic labels. If None, uses default topics.
        model_name (str): The model to use for classification.

    Returns:
        str: The most likely topic.
    """
    result = detect_topic(text, candidate_labels=candidate_labels, model_name=model_name)
    return result["top_topic"]
