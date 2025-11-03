"""
Quick demo script to test the sentiment analyzer
"""

def main():
    print("=" * 70)
    print("SENTIMENT ANALYZER - QUICK DEMO")
    print("=" * 70)

    try:
        from sentiment_analyzer import SentimentAnalyzer, quick_sentiment

        # Test 1: Quick sentiment
        print("\n1. Quick Sentiment Check:")
        print("-" * 70)
        test_texts = [
            "I absolutely love this! Best day ever!",
            "This is terrible. Worst experience of my life.",
            "It's okay, I guess. Nothing special.",
        ]

        for text in test_texts:
            sentiment = quick_sentiment(text)
            print(f"{text[:50]:<50} -> {sentiment.upper()}")

        # Test 2: Detailed analysis with large text
        print("\n2. Large Text Analysis:")
        print("-" * 70)

        # Create a huge text by repeating content
        sample_review = """
        The product arrived on time and was well packaged. The quality exceeded
        my expectations and I'm very satisfied with the purchase. The customer
        service was helpful when I had questions. However, the price is a bit
        high compared to competitors. Overall, I would recommend this to others
        who are looking for quality and don't mind paying a premium.
        """

        # Simulate a very large document (100x repetition = ~40KB of text)
        large_text = (sample_review + "\n") * 100

        analyzer = SentimentAnalyzer(method='vader', chunk_size=512, overlap=50)
        result = analyzer.analyze(large_text)

        print(f"Text size: {result.text_length:,} characters")
        print(f"Chunks processed: {result.num_chunks}")
        print(f"Overall Sentiment: {result.label.upper()}")
        print(f"Compound Score: {result.compound_score:.3f} (range: -1 to 1)")
        print(f"Positive: {result.positive_score:.3f}")
        print(f"Negative: {result.negative_score:.3f}")
        print(f"Neutral: {result.neutral_score:.3f}")

        # Test 3: Demonstrate NO SIZE LIMIT
        print("\n3. Extreme Scale Test (Very Large Document):")
        print("-" * 70)

        # Create an extremely large text (1000x = ~400KB)
        extreme_text = (sample_review + "\n") * 1000

        import time
        start = time.time()
        result = analyzer.analyze(extreme_text)
        elapsed = time.time() - start

        print(f"Text size: {result.text_length:,} characters (~{result.text_length/1024:.1f} KB)")
        print(f"Chunks processed: {result.num_chunks}")
        print(f"Processing time: {elapsed:.3f} seconds")
        print(f"Speed: {result.text_length/elapsed:,.0f} characters/second")
        print(f"Sentiment: {result.label.upper()} (score: {result.compound_score:.3f})")

        print("\n" + "=" * 70)
        print("[SUCCESS] Demo completed successfully!")
        print("=" * 70)
        print("\nKey Features Demonstrated:")
        print("  - Quick sentiment analysis")
        print("  - Large text processing with chunking")
        print("  - No size limits - can handle MB/GB of text")
        print("  - Fast processing with VADER")
        print("\nNext Steps:")
        print("  • Run: python example_usage.py (for more examples)")
        print("  • Install transformers for more accurate analysis:")
        print("    pip install transformers torch")

    except ImportError as e:
        print(f"\n[ERROR] {e}")
        print("\nPlease install required dependencies:")
        print("  pip install vaderSentiment numpy")
        print("\nOr install all dependencies:")
        print("  pip install -r requirements.txt")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
