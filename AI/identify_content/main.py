from typing import Dict, Tuple, List, Any, Optional
from AI.identify_content.feature_extraction import feature_extraction
from AI.identify_content.llm_score import llm_score
from AI.identify_content.rule_based_scoring import rule_based_scores


def runner(article : Dict[str, any], use_llm: bool) -> str:
    features = feature_extraction(article)
    if use_llm:
        llm_prediction = llm_score(features)
    else:
        score = rule_based_scores(features)

    return ""
