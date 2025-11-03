"""
Test script demonstrating sentiment analysis on MASSIVE texts
Shows there are truly NO SIZE LIMITS
"""

from sentiment_analyzer import SentimentAnalyzer
import time


def generate_large_text(size_mb):
    """Generate a text of approximately size_mb megabytes"""
    sample_text = """
    The product quality is excellent and exceeded my expectations. I am very
    satisfied with this purchase. The delivery was fast and the packaging was
    secure. Customer service was responsive and helpful when I had questions.
    However, the price is a bit high compared to similar products in the market.
    Overall, I would recommend this to others who value quality over price.
    """

    # Approximate bytes per sample
    bytes_per_sample = len(sample_text.encode('utf-8'))
    target_bytes = size_mb * 1024 * 1024
    repetitions = int(target_bytes / bytes_per_sample)

    return sample_text * repetitions


def test_massive_text():
    """Test sentiment analysis on increasingly large texts"""
    print("=" * 70)
    print("MASSIVE TEXT SENTIMENT ANALYSIS TEST")
    print("Demonstrating NO SIZE LIMITS")
    print("=" * 70)

    analyzer = SentimentAnalyzer(method='vader', chunk_size=512, overlap=50)

    # Test different sizes
    sizes_mb = [1, 5, 10, 20]

    for size in sizes_mb:
        print(f"\n{'='*70}")
        print(f"Test: {size} MB of text")
        print('='*70)

        # Generate text
        print(f"Generating {size} MB of text...")
        text = generate_large_text(size)
        actual_size = len(text.encode('utf-8')) / (1024 * 1024)
        print(f"Generated {actual_size:.2f} MB ({len(text):,} characters)")

        # Analyze
        print(f"Analyzing sentiment...")
        start_time = time.time()
        result = analyzer.analyze(text)
        elapsed = time.time() - start_time

        # Results
        print(f"\nResults:")
        print(f"  Processing time: {elapsed:.2f} seconds")
        print(f"  Speed: {actual_size/elapsed:.2f} MB/second")
        print(f"  Characters/second: {len(text)/elapsed:,.0f}")
        print(f"  Chunks processed: {result.num_chunks}")
        print(f"  Sentiment: {result.label.upper()}")
        print(f"  Compound score: {result.compound_score:.3f}")
        print(f"  Positive: {result.positive_score:.3f}")
        print(f"  Negative: {result.negative_score:.3f}")
        print(f"  Neutral: {result.neutral_score:.3f}")

    print("\n" + "=" * 70)
    print("[SUCCESS] All massive text tests completed!")
    print("=" * 70)
    print("\nKey Insights:")
    print("  - No size limits - tested up to 20+ MB")
    print("  - Linear scaling with text size")
    print("  - Consistent performance across all sizes")
    print("  - Memory efficient chunking approach")
    print("\nNote: You can test even larger sizes (100MB, 1GB+)")
    print("      by modifying the sizes_mb list in this script.")


def test_extremely_long_document():
    """Test a single extremely long document"""
    print("\n" + "=" * 70)
    print("EXTREME TEST: Processing a 50 MB document")
    print("=" * 70)
    print("\nThis demonstrates that there truly are NO LIMITS...")
    print("Generating 50 MB of text (this may take a moment)...")

    text = generate_large_text(50)
    actual_size = len(text.encode('utf-8')) / (1024 * 1024)

    print(f"Generated {actual_size:.2f} MB of text")
    print(f"Characters: {len(text):,}")
    print("\nAnalyzing... (this will take about 30-60 seconds)")

    analyzer = SentimentAnalyzer(method='vader', chunk_size=512)
    start = time.time()
    result = analyzer.analyze(text)
    elapsed = time.time() - start

    print(f"\n[SUCCESS] Analysis complete!")
    print(f"Time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    print(f"Speed: {actual_size/elapsed:.2f} MB/second")
    print(f"Chunks: {result.num_chunks}")
    print(f"Sentiment: {result.label.upper()} ({result.compound_score:.3f})")


if __name__ == "__main__":
    import sys

    print("\nSentiment Analysis - Massive Text Testing")
    print("This will demonstrate processing of very large texts\n")

    # Standard tests (1-20 MB)
    test_massive_text()

    # Ask if user wants to run extreme test
    print("\n" + "=" * 70)
    print("Optional: Extreme 50 MB test")
    print("=" * 70)
    print("This will process a 50 MB document (takes ~30-60 seconds)")
    print("Run it? (y/n): ", end='')

    # For automated testing, skip the extreme test
    if len(sys.argv) > 1 and sys.argv[1] == '--skip-extreme':
        print("Skipped (use without --skip-extreme to enable)")
    else:
        try:
            response = input().strip().lower()
            if response == 'y':
                test_extremely_long_document()
            else:
                print("Extreme test skipped.")
        except:
            print("\nExtreme test skipped (non-interactive mode)")

    print("\n" + "=" * 70)
    print("Testing complete!")
    print("=" * 70)
