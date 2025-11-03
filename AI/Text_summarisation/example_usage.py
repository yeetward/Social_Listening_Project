"""
Example usage of the Text Summarisation module.
Demonstrates how to summarize large text chunks without using LLMs.
"""

from AI.Text_summarisation import summarize_text, summarize_text_to_lines

# Example: Large news article (200+ words)
news_article = """
The global economy is facing significant headwinds as central banks worldwide continue their battle against inflation.
Interest rates have been raised multiple times over the past year, with more hikes expected in the coming months.
The Federal Reserve has signaled its commitment to bringing inflation back to its target rate of two percent.
Consumer spending has shown resilience despite higher borrowing costs and increased prices for essential goods.

The housing market has cooled considerably as mortgage rates have climbed to levels not seen in over a decade.
Home sales have declined sharply, and prices are beginning to soften in many markets across the country.
First-time homebuyers are finding it increasingly difficult to enter the market due to affordability constraints.
However, rental demand remains strong as potential buyers delay their purchase decisions.

The labor market continues to show strength with unemployment rates near historic lows.
Job openings remain elevated, though they have declined from their peak earlier this year.
Wage growth has been robust, contributing to inflationary pressures in the services sector.
Companies are still struggling to find qualified workers despite concerns about a potential recession.

Supply chain disruptions that plagued businesses during the pandemic have largely resolved.
Inventory levels have normalized, and shipping costs have returned to pre-pandemic levels.
However, geopolitical tensions continue to pose risks to global trade and commodity prices.
Energy prices have been particularly volatile, influenced by conflicts and production decisions.

The technology sector has faced significant challenges with layoffs announced by major companies.
Stock valuations have come under pressure as investors reassess growth prospects in a higher rate environment.
Cryptocurrency markets experienced extreme volatility with several high-profile collapses shaking investor confidence.
Despite setbacks, innovation continues in areas like artificial intelligence and cloud computing.

Looking ahead, economists are divided on whether the economy will achieve a soft landing or slip into recession.
Consumer sentiment has improved recently, suggesting optimism about the economic outlook.
Business investment decisions remain cautious as companies navigate uncertainty about future demand.
The coming quarters will be critical in determining the trajectory of economic growth and inflation.
"""

print("=" * 80)
print("EXAMPLE: News Article Summarization")
print("=" * 80)
print(f"Original article: {len(news_article.split())} words\n")

# Method 1: Get summary as a single paragraph (4 sentences)
print("4-Sentence Summary:")
print("-" * 80)
summary = summarize_text(news_article, num_sentences=4)
print(summary)
print()

# Method 2: Get summary as a single paragraph (5 sentences)
print("\n5-Sentence Summary:")
print("-" * 80)
summary_5 = summarize_text(news_article, num_sentences=5)
print(summary_5)
print()

# Method 3: Get summary as bullet points
print("\nBullet Point Summary (4 lines):")
print("-" * 80)
bullet_points = summarize_text_to_lines(news_article, num_lines=4)
for i, point in enumerate(bullet_points, 1):
    print(f"• {point}")

print("\n" + "=" * 80)
print("USAGE NOTES:")
print("=" * 80)
print("- No LLM required - runs locally and fast")
print("- Perfect for summarizing 200+ articles quickly")
print("- Uses TF-IDF + MMR for intelligent sentence extraction")
print("- Extracts key ideas while maintaining diversity")
print("- Typically processes an article in < 0.1 seconds")
print("=" * 80)
