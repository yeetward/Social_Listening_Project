# Pace-Unit\AI\Text_summarisation\Text_summariser.py

import sys
import os

# Add the AI directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
ai_dir = os.path.dirname(current_dir)  # Go up to AI directory
sys.path.insert(0, ai_dir)

from collection_card.gpt import load_model

def generate_summary(text:str) -> str:
    prompt = f"Summarize the following text concisely:\n\n{text}"
    summary_text = load_model(prompt, max_tokens=1500, temperature=0.7, stream=False)
    return summary_text
