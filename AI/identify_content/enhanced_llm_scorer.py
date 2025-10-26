"""
Enhanced LLM Scorer for User-Specific Content Distribution
=========================================================

This module provides AI-powered recommendations that consider user context and preferences.
"""

from openai import OpenAI
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class EnhancedLLMScorer:
    """Enhanced LLM scorer that considers user context and generates opportunities"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        Initialize the enhanced LLM scorer
        
        Args:
            api_key: OpenAI API key
            base_url: API base URL (for OpenRouter, etc.)
        """
        self.api_key = api_key or "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"
        self.base_url = base_url or "https://openrouter.ai/api/v1"
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )
    
    def recommend_distribution_channels(self, 
                                      features: Dict[str, Any], 
                                      article: Dict[str, Any], 
                                      user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate personalized distribution channel recommendations
        
        Args:
            features: Extracted article features
            article: Article data
            user_context: User context and preferences
            
        Returns:
            List of personalized recommendations
        """
        try:
            prompt = self._build_personalized_prompt(features, article, user_context)
            
            response = self.client.chat.completions.create(
                model="meta-llama/llama-3-70b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            raw_output = response.choices[0].message.content.strip()
            recommendations = self._parse_recommendations(raw_output)
            
            # Enhance recommendations with opportunities
            enhanced_recommendations = self._enhance_with_opportunities(
                recommendations, article, user_context
            )
            
            logger.info(f"Generated {len(enhanced_recommendations)} personalized recommendations")
            return enhanced_recommendations
            
        except Exception as e:
            logger.error(f"Error generating LLM recommendations: {e}")
            return []
    
    def _build_personalized_prompt(self, 
                                 features: Dict[str, Any], 
                                 article: Dict[str, Any], 
                                 user_context: Dict[str, Any]) -> str:
        """Build a personalized prompt that considers user context"""
        
        user_data = user_context.get("user_data", {})
        preferences = user_context.get("preferences", {})
        
        # Extract key user information
        user_name = user_data.get("name", "the user")
        user_role = preferences.get("role", "marketer")
        user_industry = preferences.get("industry", "general")
        preferred_channels = preferences.get("preferred_channels", [])
        company_size = preferences.get("company_size", "small")
        
        prompt = f"""
You are an expert digital content strategist and personalization specialist. 
Analyze the following article and user context to provide highly personalized 
distribution channel recommendations with specific opportunities for action.

## USER CONTEXT
- **Name**: {user_name}
- **Role**: {user_role}
- **Industry**: {user_industry}
- **Company Size**: {company_size}
- **Preferred Channels**: {', '.join(preferred_channels) if preferred_channels else 'No specific preferences'}
- **Content Interests**: {', '.join(preferences.get('content_interests', [])) if preferences.get('content_interests') else 'General interest'}
- **Personalization Level**: {preferences.get('personalization_level', 'medium')}

## ARTICLE ANALYSIS
**Title**: {article.get('title', 'N/A')}
**Content**: {article.get('content', article.get('body', ''))[:1500]}
**Source**: {article.get('source', 'Unknown')}
**Published**: {article.get('published_at', 'Unknown')}

## EXTRACTED FEATURES
{json.dumps(features, indent=2)}

## TASK
Provide personalized distribution recommendations that:
1. Align with the user's role, industry, and preferences
2. Consider the user's company size and resources
3. Include specific, actionable opportunities
4. Provide clear reasoning for each recommendation
5. Suggest optimal timing and approach

## RESPONSE FORMAT
Respond **only in valid JSON** using this exact schema:
{{
  "recommendations": [
    {{
      "channel": "string",
      "score": float,
      "reason": "string",
      "personalization_reason": "string",
      "opportunities": [
        {{
          "title": "string",
          "description": "string",
          "priority": "high|medium|low",
          "effort": "high|medium|low",
          "timeline": "string",
          "action_items": ["string"],
          "expected_outcome": "string"
        }}
      ],
      "optimal_timing": "string",
      "resource_requirements": ["string"],
      "success_metrics": ["string"]
    }}
  ],
  "overall_strategy": "string",
  "next_steps": ["string"]
}}

Focus on providing 3-5 high-quality, personalized recommendations that the user can act on immediately.
"""
        
        return prompt
    
    def _parse_recommendations(self, raw_output: str) -> List[Dict[str, Any]]:
        """Parse LLM output and extract recommendations"""
        try:
            # Try to extract JSON from the response if it's wrapped in text
            if "```" in raw_output:
                start = raw_output.find("```")
                end = raw_output.find("```", start + 3)
                if start != -1 and end != -1:
                    json_str = raw_output[start + 3:end].strip()
                    if json_str.startswith("json"):
                        json_str = json_str[4:].strip()
                    parsed = json.loads(json_str)
                else:
                    parsed = json.loads(raw_output)
            else:
                parsed = json.loads(raw_output)
            
            return parsed.get("recommendations", [])
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output as JSON: {e}")
            logger.error(f"Raw output: {raw_output}")
            return []
    
    def _enhance_with_opportunities(self, 
                                  recommendations: List[Dict[str, Any]], 
                                  article: Dict[str, Any], 
                                  user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhance recommendations with additional opportunities and context"""
        
        enhanced = []
        for rec in recommendations:
            # Add article context
            rec["article_id"] = article.get("_id")
            rec["article_title"] = article.get("title", "")
            
            # Add user context
            rec["user_id"] = user_context.get("user_id")
            rec["personalization_score"] = user_context.get("personalization_score", 0.0)
            
            # Add metadata
            rec["generated_at"] = json.dumps({"$date": {"$numberLong": str(int(__import__("time").time() * 1000))}})
            rec["model_used"] = "meta-llama/llama-3-70b-instruct"
            
            # Ensure opportunities is a list
            if "opportunities" not in rec:
                rec["opportunities"] = []
            
            enhanced.append(rec)
        
        return enhanced
    
    def generate_content_opportunities(self, 
                                     article: Dict[str, Any], 
                                     user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate specific content opportunities beyond distribution
        
        Args:
            article: Article data
            user_context: User context
            
        Returns:
            List of content opportunities
        """
        try:
            prompt = f"""
You are a content strategist. Based on this article and user context, 
suggest specific content opportunities the user can pursue.

## ARTICLE
**Title**: {article.get('title', 'N/A')}
**Content**: {article.get('content', article.get('body', ''))[:1000]}

## USER CONTEXT
**Role**: {user_context.get('preferences', {}).get('role', 'marketer')}
**Industry**: {user_context.get('preferences', {}).get('industry', 'general')}
**Company Size**: {user_context.get('preferences', {}).get('company_size', 'small')}

## TASK
Suggest 3-5 specific content opportunities such as:
- Content series ideas
- Cross-platform adaptations
- Follow-up content
- Repurposing strategies
- Engagement tactics

## RESPONSE FORMAT
Respond in valid JSON:
{{
  "opportunities": [
    {{
      "title": "string",
      "type": "content_series|repurposing|engagement|follow_up",
      "description": "string",
      "priority": "high|medium|low",
      "effort": "high|medium|low",
      "timeline": "string",
      "action_items": ["string"],
      "expected_outcome": "string"
    }}
  ]
}}
"""
            
            response = self.client.chat.completions.create(
                model="meta-llama/llama-3-70b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=1500
            )
            
            raw_output = response.choices[0].message.content.strip()
            parsed = self._parse_recommendations(raw_output)
            
            return parsed.get("opportunities", [])
            
        except Exception as e:
            logger.error(f"Error generating content opportunities: {e}")
            return []
    
    def analyze_engagement_potential(self, 
                                   article: Dict[str, Any], 
                                   user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the engagement potential of the article for the user's audience
        
        Args:
            article: Article data
            user_context: User context
            
        Returns:
            Engagement analysis
        """
        try:
            prompt = f"""
Analyze the engagement potential of this article for the user's specific audience.

## ARTICLE
**Title**: {article.get('title', 'N/A')}
**Content**: {article.get('content', article.get('body', ''))[:1000]}
**Current Engagement**: {json.dumps(article.get('engagement', {}), indent=2)}

## USER AUDIENCE
**Industry**: {user_context.get('preferences', {}).get('industry', 'general')}
**Role**: {user_context.get('preferences', {}).get('role', 'marketer')}
**Company Size**: {user_context.get('preferences', {}).get('company_size', 'small')}

## TASK
Provide an engagement analysis including:
- Predicted engagement levels
- Target audience segments
- Optimal posting times
- Engagement strategies
- Risk factors

## RESPONSE FORMAT
Respond in valid JSON:
{{
  "engagement_score": float,
  "target_audience": ["string"],
  "optimal_timing": "string",
  "engagement_strategies": ["string"],
  "risk_factors": ["string"],
  "recommendations": ["string"]
}}
"""
            
            response = self.client.chat.completions.create(
                model="meta-llama/llama-3-70b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=1000
            )
            
            raw_output = response.choices[0].message.content.strip()
            parsed = self._parse_recommendations(raw_output)
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error analyzing engagement potential: {e}")
            return {"engagement_score": 0.5, "error": str(e)}
