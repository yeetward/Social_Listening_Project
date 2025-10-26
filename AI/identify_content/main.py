from typing import Dict, Tuple, List, Any, Optional
from feature_extraction import feature_extraction
from llm_score import recommend_distribution_channels
from rule_based_scoring import rule_based_scores


def runner(article : Dict[str, any], use_llm: bool):
    features = feature_extraction(article)
    if use_llm:
        llm_prediction = recommend_distribution_channels(features, article)
        print(llm_prediction)
        return llm_prediction
    else:
        score = rule_based_scores(features)
        print(score)
        return score
    

def main():
    article = {
        "title": "Breaking: New AI Technology Transforms Content Marketing",
        "body": "A revolutionary AI-powered content marketing platform has just launched, promising to change how businesses create and distribute content. The platform uses advanced machine learning to analyze audience preferences and automatically optimize content for different channels. Early adopters report a 300% increase in engagement rates. #AI #Marketing #ContentStrategy",
        "engagement": {
            "likes": 150,
            "comments": 45,
            "shares": 80
        }
    }
    runner(article, use_llm=False)
    
if __name__ == "__main__":
    main()