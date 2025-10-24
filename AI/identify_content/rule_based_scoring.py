from typing import Dict, Tuple, List, Any, Optional

# Distribution channels we support
CHANNELS = ["email", "newsletter", "blog", "instagram", "social_media"]


def rule_based_scores(features: Dict[str, any]) -> Dict[str, float]:
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