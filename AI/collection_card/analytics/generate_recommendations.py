import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gpt
import json

def generate_personalized_ideas(profile: dict, idea_type="research_topics"):
    """
    Generate personalized recommendations based on search history
    """
    
    # Build rich context from search history
    search_context = ""
    for idx, history in enumerate(profile["search_history"], 1):
        search_context += f"\n{idx}. Subject: '{history['subject']}'\n"
        search_context += f"   Location: {history['location']} | Industry: {history['industry']}\n"
        search_context += f"   Date: {history['created_at']}\n"
        
        if history["top_articles"]:
            search_context += "   Top articles:\n"
            for article in history["top_articles"][:5]:
                search_context += f"   - [{article['source']}] {article['ai_title']}\n"
                search_context += f"     Relevance: {article.get('relevance_score', 0):.2f}\n"
        else:
            search_context += "   (No articles available)\n"
    
    prompts = {
        "research_topics": f"""
You are an AI research advisor analyzing search history to suggest new research directions.

Recent Search History with Top Results:
{search_context}

Based on this search history, suggest 5-10 NEW research topics that:
1. Build on existing interests shown in the subjects
2. Explore adjacent areas not yet searched
3. Identify emerging trends related to their focus areas
4. Consider location and industry context
5. Connect different themes from their searches

Return ONLY a valid JSON array with NO additional text:
[
  {{
    "topic": "AI-driven predictive maintenance in urban infrastructure",
    "relevance": 0.95,
    "reasoning": "Combines technology focus with urban planning interests",
    "why_explore": "Emerging trend with high impact potential",
    "related_to": ["Previous search subject 1", "Previous search subject 2"]
  }}
]
""",
        
        "trends": f"""
You are an AI analyst identifying patterns in research behavior.

Search History:
{search_context}

Analyze the search subjects, locations, industries, and identify:
1. Recurring themes and topics
2. Evolution of interests over time
3. Geographic or industry patterns
4. Potential knowledge gaps
5. Emerging focus areas

Return ONLY a valid JSON array:
[
  {{
    "trend": "Increasing focus on data-driven urban solutions",
    "confidence": 0.87,
    "evidence": "Multiple searches about data, analytics, and city planning",
    "time_period": "Recent 5 searches",
    "recommendation": "Explore smart city implementation frameworks"
  }}
]
""",
        
        "connections": f"""
You are an AI research synthesizer finding cross-topic insights.

Search History:
{search_context}

Find interesting connections between different search subjects:
1. How do these topics relate to each other?
2. What overarching themes connect them?
3. What interdisciplinary opportunities exist?
4. How do location and industry contexts create unique angles?

Return ONLY a valid JSON array:
[
  {{
    "connection": "Public-private partnerships in health technology",
    "topics_linked": ["Community Health Data Hubs", "Digital Health Literacy"],
    "insight": "Common focus on improving health outcomes through collaboration",
    "opportunity": "Integrated health data platform with educational components",
    "strength": 0.82
  }}
]
""",
        
        "deep_dive": f"""
You are an AI research advisor suggesting areas for deeper investigation.

Search History:
{search_context}

For each major subject explored, suggest specific angles for deeper research:

Return ONLY a valid JSON array:
[
  {{
    "original_subject": "Community Health Data Hubs",
    "location_context": "Sydney",
    "deep_dive_suggestions": [
      "Privacy frameworks for Australian health data sharing",
      "Case studies from comparable cities in Asia-Pacific",
      "Technical architecture for real-time data integration",
      "Stakeholder engagement strategies for public health initiatives"
    ],
    "why_important": "Surface understanding exists, but implementation details and local context needed",
    "estimated_impact": "High"
  }}
]
"""
    }
    
    prompt = prompts.get(idea_type, prompts["research_topics"])
    
    try:
        response = gpt.load_model(prompt, max_tokens=3000, temperature=0.3, stream=False)
        result = json.loads(response)
        
        if not isinstance(result, list):
            raise ValueError(f"Expected list, got {type(result)}")
        
        return result
        
    except json.JSONDecodeError as e:
        raise ValueError(f"GPT returned invalid JSON: {e}\nResponse: {response}")
    except Exception as e:
        raise RuntimeError(f"Error generating recommendations: {e}")