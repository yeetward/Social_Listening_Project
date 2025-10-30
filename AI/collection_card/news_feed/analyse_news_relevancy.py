import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gpt
import json

def news_relevancy_rag(context: dict, news_articles: list[dict]):
    """
    Analyze relevance of news articles to a company
    Args:
        context: Company context with description, competitors, etc.
        news_articles: List of dicts with 'title', 'description', 'url', etc.
    Returns:
        List of articles with relevance scores
    """
    company = context["company"]
    description = context["description"]
    competitors = ", ".join(context["competitors"])
    
    # Format news articles for the prompt
    articles_text = ""
    for idx, article in enumerate(news_articles):
        title = article.get("title", "Untitled")
        desc = article.get("description", "No description")
        source = article.get("source", "Unknown")
        articles_text += f"{idx + 1}. [{source}] {title}\n   {desc}\n\n"

    prompt = f"""
You are an AI market analyst. Your job is to assess which news articles are most relevant to {company}.

Company description:
{description}

Competitors:
{competitors}

News articles to evaluate:
{articles_text}

For each article, determine its relevance to {company} based on:
- Direct mentions of the company or its products/services
- Industry trends affecting the company
- Competitor activities
- Market conditions impacting the business
- Technology or regulatory changes relevant to operations

Return ONLY a valid JSON array with NO additional text. Each article should have:
- "index": the article number (1-based)
- "relevance": score between 0.0 and 1.0
- "reasoning": brief explanation (1-2 sentences)

Format:
[
  {{"index": 1, "relevance": 0.95, "reasoning": "Direct mention of company's new product launch"}},
  {{"index": 2, "relevance": 0.45, "reasoning": "General industry trend with indirect impact"}}
]
"""

    try:
        analysis = gpt.load_model(prompt, max_tokens=3000, temperature=0.2, stream=False)
        
        # Parse the JSON string into a Python list
        result = json.loads(analysis)
        
        # Validate it's actually a list
        if not isinstance(result, list):
            raise ValueError(f"Expected list, got {type(result)}")
        
        # Merge analysis with original article data
        enriched_results = []
        for item in result:
            idx = item.get("index", 0) - 1  # Convert to 0-based
            if 0 <= idx < len(news_articles):
                article = news_articles[idx].copy()
                article["relevance"] = item.get("relevance", 0.0)
                article["reasoning"] = item.get("reasoning", "")
                enriched_results.append(article)
        
        # Sort by relevance score (highest first)
        enriched_results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        
        return enriched_results
        
    except json.JSONDecodeError as e:
        raise ValueError(f"GPT returned invalid JSON: {e}\nResponse: {analysis}")
    except Exception as e:
        raise RuntimeError(f"Error during analysis: {e}")