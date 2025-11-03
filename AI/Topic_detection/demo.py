"""
Quick demo of the topic detection system
"""

import sys
import os
import json

# Add the AI directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
ai_dir = os.path.dirname(current_dir)
sys.path.insert(0, ai_dir)

from Topic_detection import TopicDetector

# Sample text about AI and climate change
sample_text = """
Artificial intelligence is revolutionizing climate science by processing vast amounts of environmental data.
Machine learning algorithms can predict weather patterns, analyze satellite imagery to track deforestation,
and optimize renewable energy systems. Deep learning models help scientists understand complex climate dynamics
and forecast extreme weather events with greater accuracy.

Climate change poses unprecedented challenges to global ecosystems. Rising temperatures are causing ice caps
to melt, sea levels to rise, and weather patterns to shift dramatically. Scientists use advanced computing
systems and AI to model these changes and develop mitigation strategies.

Renewable energy technologies like solar panels and wind turbines are becoming more efficient through AI
optimization. Smart grids use machine learning to balance energy supply and demand, reducing waste and
carbon emissions. Electric vehicles powered by advanced battery technology are replacing fossil fuel vehicles.

The intersection of artificial intelligence and environmental science offers hope for addressing climate
challenges. From precision agriculture that reduces water usage to AI-powered carbon capture systems,
technology plays a crucial role in building a sustainable future.
"""

print("=" * 70)
print("TOPIC DETECTION SYSTEM - DEMO")
print("=" * 70)

print("\nSample Text:")
print("-" * 70)
print(sample_text[:200] + "...")
print(f"\nTotal length: {len(sample_text)} characters\n")

# Detect topics using NLP strategy
print("=" * 70)
print("DETECTION RESULTS (NLP Strategy)")
print("=" * 70)

detector = TopicDetector(strategy="nlp")
result = detector.detect_topics(sample_text)

print("\nMain Topics:")
for i, topic in enumerate(result["main_topics"], 1):
    print(f"  {i}. {topic}")

print("\nTop Keywords:")
print(f"  {', '.join(result['keywords'][:10])}")

print("\nSubtopics by Main Topic:")
for topic, subs in list(result["subtopics"].items())[:3]:
    print(f"  {topic}:")
    for sub in subs[:3]:
        print(f"    - {sub}")

print("\n" + "=" * 70)
print("JSON OUTPUT")
print("=" * 70)
print(json.dumps(result, indent=2)[:400] + "...")

print("\n" + "=" * 70)
print("Demo complete!")
print("=" * 70)
