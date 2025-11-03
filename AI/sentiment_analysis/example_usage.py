"""
Example usage of the Sentiment Analyzer module
Demonstrates various ways to analyze sentiment on large texts
"""

from sentiment_analyzer import SentimentAnalyzer, quick_sentiment
import time


def example_1_basic_usage():
    """Basic sentiment analysis with VADER"""
    print("=" * 70)
    print("Example 1: Basic Usage with VADER (Fast, Rule-Based)")
    print("=" * 70)

    analyzer = SentimentAnalyzer(method='vader')

    # Short text
    text = "I love this product! It's absolutely amazing and exceeded my expectations."
    result = analyzer.analyze(text)

    print(f"\nText: {text}")
    print(f"Sentiment: {result.label.upper()}")
    print(f"Compound Score: {result.compound_score:.3f} (range: -1 to 1)")
    print(f"Positive: {result.positive_score:.3f}")
    print(f"Negative: {result.negative_score:.3f}")
    print(f"Neutral: {result.neutral_score:.3f}")


def example_2_large_text():
    """Analyze very large text (multiple pages)"""
    print("\n" + "=" * 70)
    print("Example 2: Large Text Analysis (Chunked Processing)")
    print("=" * 70)

    analyzer = SentimentAnalyzer(method='vader', chunk_size=512)

    # Simulate a large document
    large_text = """
    The new smartphone released this year has been receiving mixed reviews from consumers
    and critics alike. Many users praise its innovative features and sleek design, noting
    that the camera quality is exceptional and the battery life significantly improved
    compared to previous models. The display is bright and vibrant, making it perfect
    for media consumption.

    However, some customers have expressed disappointment with certain aspects of the device.
    The price point is considerably higher than competitors, which has deterred budget-conscious
    buyers. Additionally, there have been reports of minor software bugs that occasionally
    cause apps to crash unexpectedly. The lack of expandable storage is another point of
    contention among power users.

    Despite these drawbacks, the overall reception has been largely positive. Tech enthusiasts
    appreciate the cutting-edge technology and premium build quality. The customer service
    has been responsive and helpful in addressing issues. Many reviewers recommend the device
    for those who want the latest technology and are willing to pay a premium for it.

    Performance benchmarks show that the processor handles demanding tasks with ease, and
    multitasking is smooth and efficient. Gaming performance is stellar, with high frame
    rates even in graphically intensive games. The audio quality through both speakers and
    headphones is clear and immersive.

    In conclusion, while the device isn't perfect and may not be for everyone, it represents
    a solid offering in the premium smartphone market. Potential buyers should weigh the
    pros and cons based on their individual needs and budget constraints.
    """ * 10  # Repeat 10 times to simulate very large text

    start_time = time.time()
    result = analyzer.analyze(large_text)
    elapsed_time = time.time() - start_time

    print(f"\nAnalyzed {result.text_length:,} characters in {result.num_chunks} chunks")
    print(f"Processing time: {elapsed_time:.3f} seconds")
    print(f"Overall Sentiment: {result.label.upper()}")
    print(f"Compound Score: {result.compound_score:.3f}")
    print(f"Confidence: {result.score:.3f}")


def example_3_batch_processing():
    """Batch process multiple texts"""
    print("\n" + "=" * 70)
    print("Example 3: Batch Processing Multiple Texts")
    print("=" * 70)

    analyzer = SentimentAnalyzer(method='vader')

    reviews = [
        "This is the worst product I've ever bought. Complete waste of money!",
        "Pretty good, nothing special but does the job adequately.",
        "Absolutely fantastic! Best purchase I've made this year. Highly recommended!",
        "Terrible customer service and the product broke after one week.",
        "It's okay. Has some good features but also some annoying limitations.",
    ]

    results = analyzer.analyze_batch(reviews)

    for i, (review, result) in enumerate(zip(reviews, results), 1):
        print(f"\n{i}. \"{review[:60]}...\"" if len(review) > 60 else f"\n{i}. \"{review}\"")
        print(f"   -> {result.label.upper()} (score: {result.compound_score:.3f})")


def example_4_file_analysis():
    """Analyze sentiment from a file"""
    print("\n" + "=" * 70)
    print("Example 4: Analyzing Text from File")
    print("=" * 70)

    # Create a sample file
    sample_file = "sample_text.txt"
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write("""
        The conference was an incredible experience. The speakers were knowledgeable
        and engaging, presenting cutting-edge research and innovative ideas. Networking
        opportunities were abundant, and I made several valuable connections with
        professionals in my field. The venue was well-organized and the facilities
        were top-notch.

        On the downside, the registration process was confusing and time-consuming.
        Some of the sessions were overcrowded, making it difficult to find seating.
        The catering could have been better, with limited healthy options available.

        Overall, despite a few hiccups, I would definitely attend again and recommend
        it to colleagues. The knowledge gained and connections made were well worth
        the investment of time and money.
        """)

    analyzer = SentimentAnalyzer(method='vader')
    result = analyzer.analyze_file(sample_file)

    print(f"\nFile analyzed: {sample_file}")
    print(f"Sentiment: {result.label.upper()}")
    print(f"Compound Score: {result.compound_score:.3f}")
    print(f"File size: {result.text_length} characters")


def example_5_quick_sentiment():
    """Using the quick sentiment function"""
    print("\n" + "=" * 70)
    print("Example 5: Quick Sentiment Analysis (One-Liner)")
    print("=" * 70)

    texts = [
        "I'm so happy today!",
        "This is absolutely terrible.",
        "The weather is okay, I guess.",
    ]

    for text in texts:
        sentiment = quick_sentiment(text)
        print(f"\"{text}\" -> {sentiment.upper()}")


def example_6_comparison():
    """Compare different methods"""
    print("\n" + "=" * 70)
    print("Example 6: Comparing VADER (Fast) vs Transformer (Accurate)")
    print("=" * 70)

    text = """
    While the movie had some interesting moments and decent cinematography,
    the plot was predictable and the acting felt forced at times. I wouldn't
    watch it again, but it wasn't a complete waste of time.
    """

    print(f"\nAnalyzing: \"{text.strip()[:80]}...\"")

    # VADER analysis
    print("\nVADER (Rule-based, very fast):")
    start = time.time()
    vader_analyzer = SentimentAnalyzer(method='vader')
    vader_result = vader_analyzer.analyze(text)
    vader_time = time.time() - start
    print(f"  Sentiment: {vader_result.label.upper()}")
    print(f"  Compound: {vader_result.compound_score:.3f}")
    print(f"  Time: {vader_time:.4f} seconds")

    # Note: Transformer would require the libraries to be installed
    print("\nTransformer (Deep learning, more accurate):")
    print("  Install transformers and torch to use this method")
    print("  pip install transformers torch")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SENTIMENT ANALYZER - EXAMPLE USAGE")
    print("="*70 + "\n")

    try:
        example_1_basic_usage()
        example_2_large_text()
        example_3_batch_processing()
        example_4_file_analysis()
        example_5_quick_sentiment()
        example_6_comparison()

        print("\n" + "=" * 70)
        print("[SUCCESS] All examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\nMake sure to install dependencies:")
        print("  pip install -r requirements.txt")
