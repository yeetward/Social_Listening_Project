import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gpt
import json

def relevancy_rag(context: dict, trending_topics: list[str]):
    company = context["company"]
    description = context["description"]
    competitors = ", ".join(context["competitors"])
    topics = "\n".join(trending_topics)

    prompt = f"""
You are an AI market analyst. Your job is to assess which external trending topics are most relevant to {company}.

Company description:
{description}

Competitors:
{competitors}

trending topics to evaluate:
{topics}

Return ONLY a valid JSON array with NO additional text. Each topic should have a relevance score between 0.0 and 1.0.
Format:
[
  {{"topic": "relevance": 0.95}},
  {{"topic": " "relevance": 0.89}}
]
"""

    try:
        analysis = gpt.load_model(prompt, max_tokens=2000, temperature=0.2, stream=False)
        
        # Parse the JSON string into a Python list
        result = json.loads(analysis)
        
        # Validate it's actually a list
        if not isinstance(result, list):
            raise ValueError(f"Expected list, got {type(result)}")
        
        return result 
        
    except json.JSONDecodeError as e:
        raise ValueError(f"GPT returned invalid JSON: {e}\nResponse: {analysis}")
    except Exception as e:
        raise RuntimeError(f"Error during analysis: {e}")