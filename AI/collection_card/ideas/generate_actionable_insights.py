import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gpt
import json

def generate_actionable_insights(company_context: dict, recent_articles: list, insight_type="all"):
    """
    Generate actionable insights from recent articles
    
    Args:
        company_context: Dict with company name, description, competitors
        recent_articles: List of articles from ai_results
        insight_type: Type of insights to generate
            - "content": Social media posts, blogs to write
            - "opportunities": Business opportunities to pursue
            - "threats": Competitors, risks to watch
            - "all": All types of insights
    
    Returns:
        List of actionable insights
    """
    
    company_name = company_context["company"]
    description = company_context["description"]
    competitors = ", ".join(company_context["competitors"])
    
    # Format articles for analysis
    articles_text = ""
    for idx, article in enumerate(recent_articles[:20], 1):  # Limit to 20 most recent
        articles_text += f"\n{idx}. [{article.get('source', 'Unknown')}] {article.get('ai_title', 'Untitled')}\n"
        articles_text += f"   Summary: {article.get('ai_summary', 'No summary available')}\n"
        articles_text += f"   URL: {article.get('uri', 'N/A')}\n"
        articles_text += f"   Relevance: {article.get('relevance_score', 0):.2f}\n"
    
    prompts = {
        "content": f"""
You are a content strategy advisor for {company_name}.

Company: {company_name}
Description: {description}
Competitors: {competitors}

Recent articles that are relevant to the company:
{articles_text}

Analyze these articles and suggest SPECIFIC content that {company_name} should create:
- Social media posts they should make (LinkedIn, Twitter)
- Blog articles they should write
- News announcements to release
- Thought leadership pieces

For each suggestion, explain:
- What specific angle to take
- Why this is timely/relevant
- Which article(s) inspired it
- Target audience

Return ONLY a valid JSON array with this structure (use ACTUAL articles from above):
[
  {{
    "type": "linkedin_post or blog_post or twitter_post or press_release",
    "headline": "Catchy title based on the article",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "why_now": "Why this is timely",
    "source_article": "Title of the article that inspired this",
    "urgency": "high or medium or low",
    "estimated_engagement": "high or medium or low"
  }}
]
""",

        "opportunities": f"""
You are a business development advisor for {company_name}.

Company: {company_name}
Description: {description}
Competitors: {competitors}

Recent relevant articles:
{articles_text}

Identify SPECIFIC business opportunities from these articles:
- Partnership opportunities
- Market expansion possibilities
- Technology adoption opportunities
- Strategic initiatives to pursue
- Product/service gaps to fill

Return ONLY a valid JSON array with this structure (based on ACTUAL articles above):
[
  {{
    "opportunity": "Brief description of opportunity",
    "type": "partnership or technology or market_expansion or product",
    "description": "Detailed explanation",
    "potential_impact": "High/Medium/Low - explain why",
    "next_steps": ["Step 1", "Step 2", "Step 3"],
    "source_article": "Title of article that revealed this opportunity",
    "urgency": "high or medium or low",
    "confidence": 0.85
  }}
]
""",

        "threats": f"""
You are a competitive intelligence analyst for {company_name}.

Company: {company_name}
Description: {description}
Known Competitors: {competitors}

Recent relevant articles:
{articles_text}

Identify THREATS and RISKS from these articles:
- Competitor activities and announcements
- New competitors entering the market
- Market challenges
- Regulatory risks
- Technology disruptions

Return ONLY a valid JSON array with this structure (based on ACTUAL articles above):
[
  {{
    "threat": "Brief description of threat",
    "type": "competitive or regulatory or technology or market",
    "severity": "high or medium or low",
    "description": "Detailed explanation",
    "implications": ["Impact 1", "Impact 2", "Impact 3"],
    "recommended_actions": ["Action 1", "Action 2", "Action 3"],
    "source_article": "Title of article",
    "urgency": "high or medium or low",
    "timeline": "When this threat becomes relevant"
  }}
]
""",

        "all": f"""
You are a strategic advisor for {company_name}.

Company: {company_name}
Description: {description}
Competitors: {competitors}

Recent relevant articles:
{articles_text}

Generate ACTIONABLE INSIGHTS across all categories:
1. Content to create (posts, blogs, announcements)
2. Business opportunities to pursue
3. Threats/competitors to watch
4. Quick wins to capture

Analyze EACH article and determine if it presents an actionable insight for {company_name}.

Return ONLY a valid JSON array with this structure (based on ACTUAL articles above):
[
  {{
    "category": "content or opportunity or threat or quick_win",
    "action": "Clear action to take",
    "priority": "critical or high or medium or low",
    "description": "Detailed explanation of what to do and why",
    "source_article": "Title of article that inspired this",
    "estimated_effort": "low or medium or high",
    "estimated_impact": "low or medium or high",
    "urgency": "Immediate or This week or This month"
  }}
]
"""
    }
    
    prompt = prompts.get(insight_type, prompts["all"])
    
    try:
        response = gpt.load_model(prompt, max_tokens=3500, temperature=0.3, stream=False)
        
        # Strip markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]  # Remove ```json
        if response.startswith("```"):
            response = response[3:]  # Remove ```
        if response.endswith("```"):
            response = response[:-3]  # Remove trailing ```
        response = response.strip()
        
        # Parse the JSON
        result = json.loads(response)
        
        # Validate it's actually a list
        if not isinstance(result, list):
            raise ValueError(f"Expected list, got {type(result)}")
        
        return result
        
    except json.JSONDecodeError as e:
        raise ValueError(f"GPT returned invalid JSON: {e}\nResponse: {response}")
    except Exception as e:
        raise RuntimeError(f"Error generating insights: {e}")