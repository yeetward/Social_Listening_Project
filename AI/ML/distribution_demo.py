"""
Demo script for Content Distribution Classifier
Shows how to use the classifier to recommend distribution channels for articles.
"""

import sys
import json
from typing import List, Dict, Any

# Import the classifier
from content_distribution_classifier import (
    analyze_article,
    get_top_channels,
    explain_recommendation,
    analyze_articles_batch,
    CHANNELS
)

# Import MongoDB functions (optional - only if you want to save results)
try:
    from AI.Mongo.mongo_client import get_collection
    from AI.Mongo.save_distribution import (
        upsert_distribution_recommendation,
        upsert_distribution_batch,
        get_articles_by_channel
    )
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    print("[INFO] MongoDB integration not available. Running in demo mode only.\n")


# ===== EXAMPLE ARTICLES =====

SAMPLE_ARTICLES = [
    {
        "_id": "article_001",
        "title": "Breaking: Major Tech Company Announces AI Breakthrough",
        "body": """
        In a stunning announcement today, TechCorp revealed their latest AI model
        that can process natural language with unprecedented accuracy. The model,
        trained on over 1 trillion parameters, represents a significant leap forward
        in AI capabilities. Industry experts are calling it a game-changer.
        #AI #TechNews #Breaking
        """,
        "engagement": {"likes": 450, "comments": 120, "shares": 200}
    },
    {
        "_id": "article_002",
        "title": "The Complete Guide to Content Marketing in 2025",
        "body": """
        Content marketing has evolved dramatically over the past few years. In this
        comprehensive guide, we'll explore the latest strategies, tools, and best
        practices for creating compelling content that resonates with your audience.

        ## Understanding Your Audience
        The first step in any content marketing strategy is understanding who you're
        creating content for. Use data analytics to gain insights into your audience's
        preferences, behaviors, and pain points.

        ## Content Types That Work
        Different formats work for different audiences. Blog posts, videos, podcasts,
        infographics - each has its place in a well-rounded content strategy.

        ## Measuring Success
        Track key metrics like engagement rate, conversion rate, and ROI to understand
        what's working and what needs improvement. Use tools like Google Analytics
        and social media insights to gather data.

        ## Conclusion
        Content marketing in 2025 requires a data-driven approach, creativity, and
        consistent execution. Follow these principles and you'll be well on your way
        to success. Subscribe to our newsletter for more marketing insights!
        """,
        "engagement": {"likes": 85, "comments": 22, "shares": 45}
    },
    {
        "_id": "article_003",
        "title": "10 Stunning Travel Photos from Around the World",
        "body": """
        Check out these breathtaking images from our latest travel adventures!
        From the mountains of Nepal to the beaches of Bali, these photos capture
        the beauty of our planet. Which is your favorite? 📸✈️
        #Travel #Photography #Wanderlust image photo gallery
        """,
        "engagement": {"likes": 850, "comments": 95, "shares": 320}
    },
    {
        "_id": "article_004",
        "title": "Quick Tips: Boost Your Productivity Today",
        "body": """
        Want to get more done? Try these 5 simple hacks:
        1. Time blocking - schedule specific tasks
        2. Remove distractions - close unnecessary tabs
        3. Take breaks - Pomodoro technique works!
        4. Prioritize - focus on high-impact tasks first
        5. Say no - protect your time

        What's your favorite productivity tip? 💪
        #Productivity #LifeHacks #WorkSmart
        """,
        "engagement": {"likes": 320, "comments": 78, "shares": 145}
    },
    {
        "_id": "article_005",
        "title": "Exclusive Subscriber Update: New Features Coming Soon",
        "body": """
        Dear valued subscriber,

        We're excited to share some exclusive updates about the new features
        we're launching next month. As a valued member of our community, you're
        getting this information first!

        Here's what's coming:
        - Advanced analytics dashboard
        - Custom reporting tools
        - Integration with popular platforms
        - Enhanced security features

        Click here to learn more and be the first to try these features when
        they launch. Your feedback is important to us!

        Thank you for being part of our journey.
        Best regards,
        The Team
        """,
        "engagement": {"likes": 125, "comments": 35, "shares": 40}
    }
]


# ===== DEMO FUNCTIONS =====

def demo_single_article():
    """Demonstrate analysis of a single article."""
    print("=" * 60)
    print("DEMO 1: Single Article Analysis")
    print("=" * 60)

    article = SAMPLE_ARTICLES[0]

    print(f"\nArticle: {article['title']}")
    print(f"Preview: {article['body'][:100]}...")

    # Get all channel scores
    print("\n--- All Channel Scores ---")
    scores = analyze_article(article, use_llm=False)
    for channel, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(score * 20)
        print(f"{channel:15s} [{score:.3f}] {bar}")

    # Get top 3 recommendations
    print("\n--- Top 3 Recommended Channels ---")
    top_channels = get_top_channels(article, top_n=3, use_llm=False)

    for i, (channel, score) in enumerate(top_channels, 1):
        print(f"\n{i}. {channel.upper()} (Score: {score:.3f})")
        explanation = explain_recommendation(article, channel)
        print(explanation)

    print("\n" + "=" * 60 + "\n")


def demo_batch_analysis():
    """Demonstrate batch analysis of multiple articles."""
    print("=" * 60)
    print("DEMO 2: Batch Article Analysis")
    print("=" * 60)

    print(f"\nAnalyzing {len(SAMPLE_ARTICLES)} articles...\n")

    results = analyze_articles_batch(SAMPLE_ARTICLES, use_llm=False)

    for result in results:
        print(f"\nArticle: {result['title']}")
        print("Recommendations:")
        for rec in result['recommendations']:
            channel = rec['channel']
            score = rec['score']
            bar = "█" * int(score * 15)
            print(f"  {channel:15s} [{score:.3f}] {bar}")

    print("\n" + "=" * 60 + "\n")


def demo_channel_grouping():
    """Demonstrate grouping articles by recommended channel."""
    print("=" * 60)
    print("DEMO 3: Articles Grouped by Channel")
    print("=" * 60)

    # Analyze all articles
    results = analyze_articles_batch(SAMPLE_ARTICLES, use_llm=False)

    # Group by primary channel
    channel_groups: Dict[str, List[Dict[str, Any]]] = {ch: [] for ch in CHANNELS}

    for result in results:
        if result['recommendations']:
            primary_channel = result['recommendations'][0]['channel']
            channel_groups[primary_channel].append(result)

    # Display grouped results
    for channel, articles in channel_groups.items():
        if articles:
            print(f"\n{channel.upper()}: {len(articles)} article(s)")
            for article in articles:
                score = article['recommendations'][0]['score']
                print(f"  - {article['title'][:50]}... (Score: {score:.3f})")

    print("\n" + "=" * 60 + "\n")


def demo_mongodb_integration():
    """Demonstrate MongoDB integration (if available)."""
    if not MONGO_AVAILABLE:
        print("=" * 60)
        print("DEMO 4: MongoDB Integration (SKIPPED - Not Available)")
        print("=" * 60)
        print("\nTo enable MongoDB integration:")
        print("1. Ensure MongoDB is running")
        print("2. Set MONGODB_URI in your .env file")
        print("3. Run this demo again\n")
        return

    print("=" * 60)
    print("DEMO 4: MongoDB Integration")
    print("=" * 60)

    try:
        # Analyze articles
        results = analyze_articles_batch(SAMPLE_ARTICLES, use_llm=False)

        # Save to MongoDB
        print("\nSaving recommendations to MongoDB...")
        count = upsert_distribution_batch(results)
        print(f"✓ Saved {count} recommendations")

        # Query by channel
        print("\n--- Articles Recommended for Social Media ---")
        social_articles = get_articles_by_channel("social_media", min_score=0.5, limit=10)

        if social_articles:
            for doc in social_articles[:3]:  # Show first 3
                recs = [r for r in doc['recommendations'] if r['channel'] == 'social_media']
                if recs:
                    score = recs[0]['score']
                    print(f"  Article ID: {doc['article_id']} (Score: {score:.3f})")
        else:
            print("  No articles found with score >= 0.5")

        print("\n✓ MongoDB integration working successfully!")

    except Exception as e:
        print(f"\n✗ Error with MongoDB integration: {e}")
        print("  Make sure MongoDB is running and configured correctly.")

    print("\n" + "=" * 60 + "\n")


def demo_custom_weights():
    """Demonstrate using custom weights for rule vs LLM balance."""
    print("=" * 60)
    print("DEMO 5: Custom Weight Configuration")
    print("=" * 60)

    article = SAMPLE_ARTICLES[1]  # The long-form content marketing guide

    print(f"\nArticle: {article['title'][:50]}...")

    # Test different weight configurations
    configs = [
        {"rule_weight": 1.0, "llm_weight": 0.0, "name": "Rules Only"},
        {"rule_weight": 0.5, "llm_weight": 0.5, "name": "Balanced"},
        {"rule_weight": 0.3, "llm_weight": 0.7, "name": "LLM-Heavy"},
    ]

    for config in configs:
        print(f"\n--- {config['name']} (Rule: {config['rule_weight']}, LLM: {config['llm_weight']}) ---")
        top_channels = get_top_channels(
            article,
            top_n=3,
            rule_weight=config['rule_weight'],
            llm_weight=config['llm_weight'],
            use_llm=False  # Set to True to actually use LLM
        )

        for i, (channel, score) in enumerate(top_channels, 1):
            print(f"{i}. {channel:15s} (Score: {score:.3f})")

    print("\n" + "=" * 60 + "\n")


def demo_with_llm():
    """Demonstrate using the actual LLM classifier (requires transformers)."""
    print("=" * 60)
    print("DEMO 6: LLM-Based Classification (Optional)")
    print("=" * 60)

    article = SAMPLE_ARTICLES[0]

    print(f"\nArticle: {article['title']}")
    print("\nNOTE: This will download and load the BART model (~1.6GB)")
    print("      It may take several minutes on first run.")

    response = input("\nContinue with LLM classification? (y/n): ").strip().lower()

    if response == 'y':
        try:
            print("\nLoading LLM model...")
            top_channels = get_top_channels(article, top_n=3, use_llm=True)

            print("\n--- LLM-Based Recommendations ---")
            for i, (channel, score) in enumerate(top_channels, 1):
                print(f"{i}. {channel:15s} (Score: {score:.3f})")

            print("\n✓ LLM classification completed successfully!")

        except Exception as e:
            print(f"\n✗ Error: {e}")
            print("  Make sure 'transformers' and 'torch' are installed.")
    else:
        print("\nSkipped LLM classification.")

    print("\n" + "=" * 60 + "\n")


# ===== MAIN =====

def main():
    """Run all demos."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "Content Distribution Classifier Demo" + " " * 11 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    # Run demos
    demo_single_article()
    input("Press Enter to continue to next demo...")

    demo_batch_analysis()
    input("Press Enter to continue to next demo...")

    demo_channel_grouping()
    input("Press Enter to continue to next demo...")

    demo_mongodb_integration()
    input("Press Enter to continue to next demo...")

    demo_custom_weights()
    input("Press Enter to continue to next demo...")

    demo_with_llm()

    print("\n" + "=" * 60)
    print("All demos completed!")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Integrate with your existing article pipeline")
    print("2. Adjust weights based on your business needs")
    print("3. Connect to your MongoDB database")
    print("4. Optional: Enable LLM classification for better accuracy")
    print("\nFor production use, see: AI/ML/content_distribution_classifier.py")
    print()


if __name__ == "__main__":
    main()
