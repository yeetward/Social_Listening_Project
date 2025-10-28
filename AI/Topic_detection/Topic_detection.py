import sys
import os

# Add the AI directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
ai_dir = os.path.dirname(current_dir)  # Go up to AI directory
sys.path.insert(0, ai_dir)

from collection_card.gpt import load_model

def detect_topic_simple(text:str) -> str:
    return "topic"