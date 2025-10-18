try:
    from transformers import pipeline
except Exception:
    pipeline = None


# Lazily-initialized cached summarizer to avoid reloading the model on every call
_SUMMARIZER = None


def _get_summarizer(model_name="facebook/bart-large-cnn"):
    """Return a cached summarizer pipeline. Raises RuntimeError if transformers is not available."""
    global _SUMMARIZER
    if pipeline is None:
        raise RuntimeError("transformers is not installed or failed to import. Install 'transformers' to use generate_summary.")
    if _SUMMARIZER is None:
        _SUMMARIZER = pipeline("summarization", model=model_name)
    return _SUMMARIZER


def generate_summary(text, max_length=130, min_length=30, model_name="facebook/bart-large-cnn"):
    """Generate a short summary for `text`.

    Notes:
    - The heavy model is cached after the first call.
    - If the input is much longer than the model's context, it will be truncated at ~1024 words.
    """
    summarizer = _get_summarizer(model_name=model_name)

    # Handle long texts by chunking/truncating if needed (word-based simple truncation)
    max_input_length = 1024
    if len(text.split()) > max_input_length:
        text = " ".join(text.split()[:max_input_length])

    summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
    return summary[0]["summary_text"]


if __name__ == "__main__":
    input_text = """
    Artificial intelligence is transforming the world in unprecedented ways. 
    From healthcare to finance, AI systems are being deployed to solve complex 
    problems and automate tasks that were once thought to require human intelligence. 
    Machine learning algorithms can now analyze vast amounts of data, recognize patterns, 
    and make predictions with remarkable accuracy. However, this rapid advancement also 
    raises important ethical questions about privacy, bias, and the future of work.
    """
    
    summary = generate_summary(input_text)
    print("Summary:", summary)