import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ArticleEvaluator:
    """
    LLM-based article evaluator that determines:
    1. Whether an article is worth posting
    2. What type of content it should be (newsletter, blog, youtube, etc.)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the evaluator with OpenAI API key.

        Args:
            api_key: OpenAI API key. If not provided, will look for OPENAI_API_KEY env variable
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable or pass api_key parameter")

        self.client = OpenAI(api_key=self.api_key)

        # Content type definitions
        self.content_types = {
            "newsletter": "Email newsletter - curated, personalized content for subscribers",
            "blog": "Blog post - in-depth, long-form content with detailed analysis",
            "youtube": "YouTube video - visual, engaging content suitable for video format",
            "social_media": "Social media post - short, engaging content with hashtags/mentions",
            "podcast": "Podcast episode - conversational, audio-friendly content",
            "infographic": "Infographic - data-driven, visual content",
            "case_study": "Case study - detailed analysis with real-world examples",
            "tutorial": "Tutorial/How-to - step-by-step instructional content"
        }

    def evaluate_article(self, article: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate an article using LLM to determine if it's worth posting and what type.

        Args:
            article: Dictionary containing article data (title, body, etc.)
            features: Dictionary containing extracted features from feature_extraction

        Returns:
            Dictionary with evaluation results:
            {
                "is_worth_posting": bool,
                "confidence_score": float (0-1),
                "recommended_content_types": list[str],
                "reasoning": str,
                "suggested_improvements": list[str],
                "error": str (only present if an error occurred)
            }
        """
        # Validate inputs
        if not isinstance(article, dict):
            raise ValueError("article must be a dictionary")
        if not isinstance(features, dict):
            raise ValueError("features must be a dictionary")
        if "title" not in article and "body" not in article:
            raise ValueError("article must contain at least 'title' or 'body'")

        # Prepare the prompt
        prompt = self._build_evaluation_prompt(article, features)

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using gpt-4o-mini for cost-effectiveness
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content strategist who evaluates articles and recommends the best content formats for distribution."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent results
                response_format={"type": "json_object"}
            )

            # Parse the response
            result = self._parse_llm_response(response.choices[0].message.content)
            return result

        except Exception as e:
            return {
                "error": str(e),
                "is_worth_posting": False,
                "confidence_score": 0.0,
                "recommended_content_types": [],
                "reasoning": f"Error during evaluation: {str(e)}",
                "suggested_improvements": []
            }

    def _build_evaluation_prompt(self, article: Dict[str, Any], features: Dict[str, Any]) -> str:
        """Build the prompt for LLM evaluation."""

        title = article.get("title", "No title provided")
        body = article.get("body", "No body provided")

        # Smart body truncation: keep first 800 and last 200 chars for better context
        max_chars = 1000
        if len(body) > max_chars:
            truncated_body = body[:800] + "\n\n[... content truncated ...]\n\n" + body[-200:]
        else:
            truncated_body = body

        # Build feature summary
        feature_summary = "\n".join([f"- {key}: {value}" for key, value in features.items()])

        # Build content types description
        content_types_desc = "\n".join([f"- {key}: {desc}" for key, desc in self.content_types.items()])

        prompt = f"""
Evaluate the following article and determine:
1. Whether it's worth posting (quality, relevance, engagement potential)
2. What content type(s) would be most suitable for distribution

Article Information:
---
Title: {title}
Body: {truncated_body}
---

Extracted Features:
{feature_summary}

Available Content Types:
{content_types_desc}

Please provide your evaluation in JSON format with the following structure:
{{
    "is_worth_posting": true/false,
    "confidence_score": 0.0-1.0,
    "recommended_content_types": ["type1", "type2"],
    "reasoning": "Your detailed reasoning for the recommendation",
    "suggested_improvements": ["improvement1", "improvement2"]
}}

Consider:
- Content quality and depth
- Engagement potential based on features
- Suitability for different formats
- Target audience fit
- Uniqueness and value proposition
"""
        return prompt

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the LLM response into structured format."""
        try:
            result = json.loads(response_text)

            # Validate required fields
            required_fields = ["is_worth_posting", "confidence_score", "recommended_content_types", "reasoning"]
            for field in required_fields:
                if field not in result:
                    result[field] = self._get_default_value(field)

            # Ensure suggested_improvements exists
            if "suggested_improvements" not in result:
                result["suggested_improvements"] = []

            # Validate and filter content types to only include valid ones
            if "recommended_content_types" in result:
                valid_types = [ct for ct in result["recommended_content_types"] if ct in self.content_types]
                result["recommended_content_types"] = valid_types

            return result

        except json.JSONDecodeError:
            return {
                "is_worth_posting": False,
                "confidence_score": 0.0,
                "recommended_content_types": [],
                "reasoning": "Failed to parse LLM response",
                "suggested_improvements": []
            }

    def _get_default_value(self, field: str) -> Any:
        """Get default value for a missing field."""
        defaults = {
            "is_worth_posting": False,
            "confidence_score": 0.0,
            "recommended_content_types": [],
            "reasoning": "No reasoning provided",
            "suggested_improvements": []
        }
        return defaults.get(field)


def evaluate_article_with_llm(article: Dict[str, Any], features: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to evaluate an article.

    Args:
        article: Dictionary containing article data (title, body, etc.)
        features: Dictionary containing extracted features
        api_key: Optional OpenAI API key

    Returns:
        Evaluation results dictionary
    """
    evaluator = ArticleEvaluator(api_key=api_key)
    return evaluator.evaluate_article(article, features)


# Example usage
if __name__ == "__main__":
    # Example article
    example_article = {
        "title": "The Future of AI: A Comprehensive Analysis",
        "body": """
        Artificial Intelligence is rapidly transforming our world. In this comprehensive analysis,
        we explore the latest developments in AI technology, from large language models to
        autonomous systems. We'll examine the implications for various industries and discuss
        the ethical considerations that come with these powerful tools.

        ## Key Developments
        - Large Language Models
        - Computer Vision Advances
        - Robotics Integration

        ## Industry Impact
        The impact on healthcare, finance, and education has been profound...
        """
    }

    # Example features (would come from feature_extraction.py)
    example_features = {
        "word_count": 450,
        "char_count": 2500,
        "total_engagement": 150,
        "has_images": True,
        "has_video": False,
        "has_links": True,
        "is_urgent": False,
        "has_sections": True,
        "has_detailed_analysis": True,
        "has_hashtags": False,
        "has_mentions": False,
        "is_short_form": False,
        "is_personalized": False,
        "has_cta": True
    }

    # Evaluate
    try:
        result = evaluate_article_with_llm(example_article, example_features)

        print("=" * 50)
        print("ARTICLE EVALUATION RESULTS")
        print("=" * 50)
        print(f"\nWorth Posting: {result['is_worth_posting']}")
        print(f"Confidence Score: {result['confidence_score']:.2f}")
        print(f"\nRecommended Content Types:")
        for content_type in result['recommended_content_types']:
            print(f"  - {content_type}")
        print(f"\nReasoning:\n{result['reasoning']}")

        if result.get('suggested_improvements'):
            print(f"\nSuggested Improvements:")
            for improvement in result['suggested_improvements']:
                print(f"  - {improvement}")

    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure to set OPENAI_API_KEY environment variable")
