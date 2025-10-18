"""
Content Distribution Classifier - Hybrid Approach
Recommends the best distribution channels for articles (email, newsletter, blog, instagram, social media)
Combines rule-based feature extraction with LLM-based classification for intelligent recommendations.
"""

from typing import Dict, List, Tuple, Any, Optional
import re

try:
    from transformers import pipeline
except Exception:
    pipeline = None


# Distribution channels we support
CHANNELS = ["email", "newsletter", "blog", "instagram", "social_media"]

# Lazily-initialized cached classifier
_CLASSIFIER = None


def _get_classifier(model_name="facebook/bart-large-mnli"):
    """Return a cached zero-shot classifier pipeline."""
    global _CLASSIFIER
    if pipeline is None:
        raise RuntimeError(
            "transformers is not installed. Install 'transformers' to use LLM-based classification."
        )
    if _CLASSIFIER is None:
        _CLASSIFIER = pipeline("zero-shot-classification", model=model_name)
    return _CLASSIFIER


# ===== FEATURE EXTRACTION (Rule-Based) =====

def extract_features(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract features from an article for rule-based analysis.

    Args:
        article: Dictionary with 'title', 'body', 'engagement', etc.

    Returns:
        Dictionary of extracted features
    """
    title = article.get("title", "")
    body = article.get("body", "")
    full_text = f"{title} {body}"

    # Text length features
    word_count = len(full_text.split())
    char_count = len(full_text)

    # Engagement metrics
    engagement = article.get("engagement", {})
    if isinstance(engagement, dict):
        likes = engagement.get("likes", 0)
        comments = engagement.get("comments", 0)
        shares = engagement.get("shares", 0)
        total_engagement = likes + comments + shares
    else:
        total_engagement = 0

    # Content type indicators
    has_images = "image" in body.lower() or "photo" in body.lower() or "img" in body.lower()
    has_video = "video" in body.lower() or "watch" in body.lower()
    has_links = "http" in body or "www." in body

    # Urgency indicators
    urgency_keywords = ["breaking", "urgent", "alert", "now", "today", "just in", "update"]
    is_urgent = any(keyword in full_text.lower() for keyword in urgency_keywords)

    # Long-form indicators
    has_sections = any(marker in body for marker in ["\n\n", "##", "###"])
    has_detailed_analysis = word_count > 500

    # Social media indicators
    has_hashtags = "#" in full_text
    has_mentions = "@" in full_text
    is_short_form = word_count < 150

    # Email indicators
    is_personalized = any(word in full_text.lower() for word in ["you", "your", "subscribe"])
    has_cta = any(phrase in full_text.lower() for phrase in ["click", "read more", "learn more", "sign up"])

    return {
        "word_count": word_count,
        "char_count": char_count,
        "total_engagement": total_engagement,
        "has_images": has_images,
        "has_video": has_video,
        "has_links": has_links,
        "is_urgent": is_urgent,
        "has_sections": has_sections,
        "has_detailed_analysis": has_detailed_analysis,
        "has_hashtags": has_hashtags,
        "has_mentions": has_mentions,
        "is_short_form": is_short_form,
        "is_personalized": is_personalized,
        "has_cta": has_cta,
    }


def rule_based_scores(features: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate rule-based scores for each distribution channel.

    Args:
        features: Dictionary of extracted features

    Returns:
        Dictionary mapping channel names to scores (0-1)
    """
    scores = {channel: 0.0 for channel in CHANNELS}

    # EMAIL: Long-form, personalized, high-value content with CTA
    scores["email"] = 0.0
    if features["word_count"] > 300:
        scores["email"] += 0.3
    if features["has_detailed_analysis"]:
        scores["email"] += 0.2
    if features["is_personalized"]:
        scores["email"] += 0.2
    if features["has_cta"]:
        scores["email"] += 0.2
    if features["has_sections"]:
        scores["email"] += 0.1

    # NEWSLETTER: Curated, timely, medium-length content
    scores["newsletter"] = 0.0
    if 200 <= features["word_count"] <= 800:
        scores["newsletter"] += 0.3
    if features["is_urgent"]:
        scores["newsletter"] += 0.2
    if features["has_links"]:
        scores["newsletter"] += 0.2
    if features["total_engagement"] > 50:
        scores["newsletter"] += 0.2
    if not features["is_short_form"]:
        scores["newsletter"] += 0.1

    # BLOG: Evergreen, long-form, detailed content
    scores["blog"] = 0.0
    if features["word_count"] > 500:
        scores["blog"] += 0.4
    if features["has_sections"]:
        scores["blog"] += 0.2
    if features["has_detailed_analysis"]:
        scores["blog"] += 0.2
    if features["has_images"] or features["has_video"]:
        scores["blog"] += 0.1
    if not features["is_urgent"]:  # Evergreen content
        scores["blog"] += 0.1

    # INSTAGRAM: Visual, short, engaging content
    scores["instagram"] = 0.0
    if features["has_images"] or features["has_video"]:
        scores["instagram"] += 0.4
    if features["is_short_form"]:
        scores["instagram"] += 0.3
    if features["has_hashtags"]:
        scores["instagram"] += 0.2
    if features["total_engagement"] > 100:
        scores["instagram"] += 0.1

    # SOCIAL_MEDIA (Twitter/LinkedIn): Short, urgent, engaging
    scores["social_media"] = 0.0
    if features["is_short_form"]:
        scores["social_media"] += 0.3
    if features["is_urgent"]:
        scores["social_media"] += 0.3
    if features["has_hashtags"] or features["has_mentions"]:
        scores["social_media"] += 0.2
    if features["total_engagement"] > 50:
        scores["social_media"] += 0.1
    if features["has_links"]:
        scores["social_media"] += 0.1

    # Normalize to 0-1 range
    for channel in scores:
        scores[channel] = min(1.0, max(0.0, scores[channel]))

    return scores


# ===== LLM-BASED CLASSIFICATION =====

def llm_based_scores(article: Dict[str, Any], use_llm: bool = True) -> Dict[str, float]:
    """
    Use zero-shot classification to score distribution channels.

    Args:
        article: Dictionary with 'title' and 'body'
        use_llm: Whether to use LLM (if False, returns neutral scores)

    Returns:
        Dictionary mapping channel names to confidence scores (0-1)
    """
    if not use_llm:
        return {channel: 0.5 for channel in CHANNELS}

    try:
        classifier = _get_classifier()

        # Prepare text (limit length for performance)
        title = article.get("title", "")
        body = article.get("body", "")
        text = f"{title}. {body}"

        # Truncate to avoid memory issues (keep first ~500 words)
        words = text.split()
        if len(words) > 500:
            text = " ".join(words[:500])

        # Define hypotheses for each channel
        hypothesis_template = [
            "This content is best suited for email marketing campaigns",
            "This content is perfect for a newsletter",
            "This content should be published as a blog post",
            "This content is ideal for Instagram posts",
            "This content is great for social media like Twitter or LinkedIn"
        ]

        # Run classification
        result = classifier(text, hypothesis_template, multi_label=True)

        # Map results to channel scores
        scores = {}
        for label, score in zip(result["labels"], result["scores"]):
            if "email" in label.lower():
                scores["email"] = float(score)
            elif "newsletter" in label.lower():
                scores["newsletter"] = float(score)
            elif "blog" in label.lower():
                scores["blog"] = float(score)
            elif "instagram" in label.lower():
                scores["instagram"] = float(score)
            elif "social media" in label.lower():
                scores["social_media"] = float(score)

        # Ensure all channels have scores
        for channel in CHANNELS:
            if channel not in scores:
                scores[channel] = 0.0

        return scores

    except Exception as e:
        print(f"[WARN] LLM classification failed: {e}")
        # Fallback to neutral scores
        return {channel: 0.5 for channel in CHANNELS}


# ===== HYBRID COMBINER =====

def analyze_article(
    article: Dict[str, Any],
    rule_weight: float = 0.6,
    llm_weight: float = 0.4,
    use_llm: bool = True
) -> Dict[str, float]:
    """
    Analyze an article and return distribution channel scores.

    Combines rule-based and LLM-based approaches.

    Args:
        article: Dictionary with article data (title, body, engagement, etc.)
        rule_weight: Weight for rule-based scores (default 0.6)
        llm_weight: Weight for LLM-based scores (default 0.4)
        use_llm: Whether to use LLM classification (default True)

    Returns:
        Dictionary mapping channel names to combined scores (0-1)
    """
    # Extract features and get rule-based scores
    features = extract_features(article)
    rule_scores = rule_based_scores(features)

    # Get LLM-based scores
    llm_scores = llm_based_scores(article, use_llm=use_llm)

    # Combine scores
    combined_scores = {}
    for channel in CHANNELS:
        combined_scores[channel] = (
            rule_weight * rule_scores[channel] +
            llm_weight * llm_scores[channel]
        )

    return combined_scores


def get_top_channels(
    article: Dict[str, Any],
    top_n: int = 3,
    rule_weight: float = 0.6,
    llm_weight: float = 0.4,
    use_llm: bool = True,
    min_score: float = 0.3
) -> List[Tuple[str, float]]:
    """
    Get the top N recommended distribution channels for an article.

    Args:
        article: Dictionary with article data
        top_n: Number of top channels to return
        rule_weight: Weight for rule-based scores
        llm_weight: Weight for LLM-based scores
        use_llm: Whether to use LLM classification
        min_score: Minimum score threshold (0-1)

    Returns:
        List of (channel_name, score) tuples, sorted by score descending
    """
    scores = analyze_article(article, rule_weight, llm_weight, use_llm)

    # Filter by minimum score and sort
    filtered_scores = [(ch, sc) for ch, sc in scores.items() if sc >= min_score]
    filtered_scores.sort(key=lambda x: x[1], reverse=True)

    return filtered_scores[:top_n]


def explain_recommendation(
    article: Dict[str, Any],
    channel: str,
    rule_weight: float = 0.6,
    llm_weight: float = 0.4
) -> str:
    """
    Provide an explanation for why a channel was recommended.

    Args:
        article: Dictionary with article data
        channel: Channel name to explain
        rule_weight: Weight for rule-based scores
        llm_weight: Weight for LLM-based scores

    Returns:
        Human-readable explanation string
    """
    if channel not in CHANNELS:
        return f"Unknown channel: {channel}"

    features = extract_features(article)
    rule_scores = rule_based_scores(features)

    explanations = []

    # Channel-specific explanations based on features
    if channel == "email":
        if features["word_count"] > 300:
            explanations.append(f"Long-form content ({features['word_count']} words)")
        if features["is_personalized"]:
            explanations.append("Personalized language detected")
        if features["has_cta"]:
            explanations.append("Contains call-to-action")
        if features["has_detailed_analysis"]:
            explanations.append("In-depth analysis")

    elif channel == "newsletter":
        if 200 <= features["word_count"] <= 800:
            explanations.append(f"Ideal length for newsletters ({features['word_count']} words)")
        if features["is_urgent"]:
            explanations.append("Timely/urgent content")
        if features["total_engagement"] > 50:
            explanations.append(f"High engagement potential ({features['total_engagement']} interactions)")

    elif channel == "blog":
        if features["word_count"] > 500:
            explanations.append(f"Comprehensive content ({features['word_count']} words)")
        if features["has_sections"]:
            explanations.append("Well-structured with sections")
        if not features["is_urgent"]:
            explanations.append("Evergreen content")

    elif channel == "instagram":
        if features["has_images"] or features["has_video"]:
            explanations.append("Visual content detected")
        if features["is_short_form"]:
            explanations.append(f"Concise format ({features['word_count']} words)")
        if features["has_hashtags"]:
            explanations.append("Contains hashtags")

    elif channel == "social_media":
        if features["is_short_form"]:
            explanations.append(f"Short, shareable ({features['word_count']} words)")
        if features["is_urgent"]:
            explanations.append("Breaking/trending content")
        if features["has_hashtags"]:
            explanations.append("Social media optimized with hashtags")

    score = rule_scores[channel]
    confidence = "High" if score > 0.7 else "Medium" if score > 0.4 else "Low"

    explanation_text = f"{channel.upper()} (Confidence: {confidence}, Score: {score:.2f})\n"
    if explanations:
        explanation_text += "Reasons:\n- " + "\n- ".join(explanations)
    else:
        explanation_text += "No strong indicators for this channel."

    return explanation_text


# ===== BATCH PROCESSING =====

def analyze_articles_batch(
    articles: List[Dict[str, Any]],
    rule_weight: float = 0.6,
    llm_weight: float = 0.4,
    use_llm: bool = True
) -> List[Dict[str, Any]]:
    """
    Analyze multiple articles and return recommendations for each.

    Args:
        articles: List of article dictionaries
        rule_weight: Weight for rule-based scores
        llm_weight: Weight for LLM-based scores
        use_llm: Whether to use LLM classification

    Returns:
        List of dictionaries with article ID and recommendations
    """
    results = []

    for article in articles:
        article_id = article.get("_id", "unknown")
        top_channels = get_top_channels(
            article,
            top_n=3,
            rule_weight=rule_weight,
            llm_weight=llm_weight,
            use_llm=use_llm
        )

        results.append({
            "_id": article_id,
            "title": article.get("title", "")[:100],  # Truncate for display
            "recommendations": [
                {"channel": ch, "score": float(sc)}
                for ch, sc in top_channels
            ]
        })

    return results


# ===== USAGE EXAMPLE =====

if __name__ == "__main__":
    # Example article
    sample_article = {
        "title": "Breaking: New AI Technology Transforms Content Marketing",
        "body": """
        A revolutionary AI-powered content marketing platform has just launched,
        promising to change how businesses create and distribute content.
        The platform uses advanced machine learning to analyze audience preferences
        and automatically optimize content for different channels. Early adopters
        report a 300% increase in engagement rates. #AI #Marketing #ContentStrategy
        """,
        "engagement": {
            "likes": 150,
            "comments": 45,
            "shares": 80
        }
    }

    print("=== Content Distribution Analysis ===\n")

    # Get all scores
    scores = analyze_article(sample_article, use_llm=False)
    print("Channel Scores:")
    for channel, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        print(f"  {channel}: {score:.3f}")

    print("\n" + "="*40 + "\n")

    # Get top recommendations
    top_channels = get_top_channels(sample_article, top_n=3, use_llm=False)
    print("Top 3 Recommended Channels:")
    for i, (channel, score) in enumerate(top_channels, 1):
        print(f"\n{i}. {channel.upper()} (Score: {score:.3f})")
        print(explain_recommendation(sample_article, channel))
