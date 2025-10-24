from openai import OpenAI
import json
from typing import Dict, Tuple, List, Any, Optional

def recommend_distribution_channels(features: dict, article_text: str) -> list[dict]:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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"
    )

    prompt = f"""
    You are an expert digital content strategist. 
    Analyze the following article and its metadata to recommend the best
    distribution channels (e.g., company blog, newsletter, LinkedIn post, 
    X/Twitter, Reddit, email to clients, etc.).
cal
    Respond **only in valid JSON** using this exact schema:
    {{
      "recommendations": [
        {{
          "channel": "string",
          "score": float,
          "reason": "string"
        }}
      ]
    }}

    ### Metadata:
    {json.dumps(features, indent=2)}

    ### Content:
    {article_text[:2000]}
    """

    response = client.chat.completions.create(
        model="meta-llama/llama-3-70b-instruct",  # or any other model you prefer
        messages=[{"role": "user", "content": prompt}]
    )

    raw_output = response.choices[0].message.content.strip()

    # Attempt to safely parse model output as JSON
    try:
        parsed = json.loads(raw_output)
        return parsed.get("recommendations", [])
    except json.JSONDecodeError:
        print("Model did not return valid JSON. Raw output:")
        print(raw_output)
        return []
