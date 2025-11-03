"""
Example Usage of Topic Detection System
Demonstrates different strategies and use cases
"""

import sys
import os

# Add the AI directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
ai_dir = os.path.dirname(current_dir)
sys.path.insert(0, ai_dir)

from Topic_detection import TopicDetector, detect_topics, detect_topics_json


def example_short_text():
    """Example with short text"""
    print("=" * 80)
    print("EXAMPLE 1: Short Text - NLP Strategy")
    print("=" * 80)

    text = """
    Artificial intelligence and machine learning are revolutionizing healthcare.
    Deep learning models can now diagnose diseases from medical images with high accuracy.
    Natural language processing helps doctors extract insights from patient records.
    AI-powered drug discovery is accelerating pharmaceutical research.
    """

    detector = TopicDetector(strategy="nlp")
    result = detector.detect_topics(text)

    print(f"\nInput text length: {len(text)} characters")
    print("\nDetected Topics:")
    print(f"Main Topics: {result['main_topics']}")
    print(f"Keywords: {result['keywords']}")
    print(f"Subtopics: {result['subtopics']}")
    print()


def example_long_text():
    """Example with longer text"""
    print("=" * 80)
    print("EXAMPLE 2: Long Text - Hybrid Strategy")
    print("=" * 80)

    text = """
    Climate change is one of the most pressing challenges facing humanity today.
    Rising global temperatures are causing unprecedented environmental disruptions.
    The melting of polar ice caps is accelerating sea level rise, threatening coastal communities worldwide.

    Scientific consensus indicates that human activities, particularly the burning of fossil fuels,
    are the primary drivers of recent climate change. Carbon dioxide emissions from industrial processes,
    transportation, and energy generation have reached record levels.

    Renewable energy technologies offer promising solutions. Solar power has become increasingly cost-competitive,
    with photovoltaic efficiency improving year over year. Wind energy capacity has expanded dramatically,
    both onshore and offshore. Electric vehicles are gaining market share, reducing transportation emissions.

    International cooperation is essential for addressing climate change. The Paris Agreement represents
    a landmark effort to limit global warming to well below 2 degrees Celsius. However, achieving these
    targets requires significant policy changes, technological innovation, and behavioral shifts.

    Adaptation strategies are equally important. Cities are implementing green infrastructure to manage
    increased flooding and heat waves. Agriculture is developing drought-resistant crops. Coastal regions
    are investing in protective barriers and early warning systems.
    """

    detector = TopicDetector(strategy="hybrid")
    result = detector.detect_topics(text)

    print(f"\nInput text length: {len(text)} characters")
    print("\nDetected Topics:")
    print(f"Main Topics: {result['main_topics']}")
    print(f"Keywords: {result['keywords'][:10]}...")  # Show first 10 keywords
    print(f"Number of subtopics: {len(result['subtopics'])}")
    print()


def example_llm_strategy():
    """Example using LLM strategy (requires Groq API)"""
    print("=" * 80)
    print("EXAMPLE 3: LLM-Based Detection")
    print("=" * 80)

    text = """
    Blockchain technology is transforming the financial services industry.
    Cryptocurrencies like Bitcoin and Ethereum enable peer-to-peer transactions
    without intermediaries. Smart contracts automate complex business processes.
    Decentralized finance (DeFi) platforms offer lending, borrowing, and trading
    services without traditional banks. Non-fungible tokens (NFTs) are creating
    new markets for digital art and collectibles.
    """

    print(f"\nInput text length: {len(text)} characters")
    print("Note: This requires a valid Groq API key")

    try:
        detector = TopicDetector(strategy="llm")
        result = detector.detect_topics(text)

        print("\nDetected Topics:")
        print(f"Main Topics: {result['main_topics']}")
        print(f"Keywords: {result['keywords']}")

        print("\nSubtopics by Main Topic:")
        for topic, subs in result['subtopics'].items():
            print(f"  {topic}: {subs}")
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure GROQ_API_KEY is set in your environment")
    print()


def example_json_output():
    """Example with JSON output"""
    print("=" * 80)
    print("EXAMPLE 4: JSON Output Format")
    print("=" * 80)

    text = """
    Cybersecurity threats are evolving rapidly. Ransomware attacks target critical
    infrastructure and healthcare systems. Phishing campaigns exploit social engineering
    techniques. Zero-day vulnerabilities pose significant risks to organizations.
    Multi-factor authentication and encryption are essential security measures.
    """

    json_result = detect_topics_json(text, strategy="nlp")
    print("\nJSON Output:")
    print(json_result)
    print()


def example_very_long_text():
    """Example with very long text (chunking demonstration)"""
    print("=" * 80)
    print("EXAMPLE 5: Very Long Text (Automatic Chunking)")
    print("=" * 80)

    # Create a very long text by repeating content
    base_text = """
    Space exploration continues to push the boundaries of human achievement.
    NASA's Mars missions are searching for signs of ancient life. The James Webb
    Space Telescope is revealing distant galaxies. Private companies like SpaceX
    are developing reusable rockets. The Artemis program aims to return humans
    to the Moon. International cooperation on the International Space Station
    demonstrates peaceful collaboration in space.
    """

    # Repeat to create long document
    long_text = (base_text + " ") * 50  # ~5000 words

    detector = TopicDetector(strategy="nlp", max_chunk_size=1000)
    result = detector.detect_topics(long_text)

    print(f"\nInput text length: {len(long_text)} characters")
    print(f"Approximate word count: {len(long_text.split())}")
    print("\nDetected Topics:")
    print(f"Main Topics: {result['main_topics']}")
    print(f"Top Keywords: {result['keywords'][:8]}")
    print()


def example_convenience_functions():
    """Example using convenience functions"""
    print("=" * 80)
    print("EXAMPLE 6: Convenience Functions")
    print("=" * 80)

    text = "Quantum computing uses quantum bits or qubits to perform calculations."

    # Using the simple function-based API
    result = detect_topics(text, strategy="nlp")
    print(f"\nText: {text}")
    print(f"Main Topics: {result['main_topics']}")
    print()


if __name__ == "__main__":
    print("\n")
    print("#" * 80)
    print("#  TOPIC DETECTION SYSTEM - EXAMPLES")
    print("#" * 80)
    print()

    # Run examples
    example_short_text()
    example_long_text()
    example_json_output()
    example_convenience_functions()
    example_very_long_text()

    # LLM example (commented out by default - requires API key)
    # example_llm_strategy()

    print("=" * 80)
    print("All examples completed!")
    print("=" * 80)
