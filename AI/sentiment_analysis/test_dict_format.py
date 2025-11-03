"""
Example usage of analyze_text_dict function
"""

from sentiment_analyzer import analyze_text_dict

# Example input: list of dictionaries with "Text" key
data = [
    {"Text": "I love this product! It's amazing and works perfectly."},
    {"Text": "This is horrendous but amazing."},
    {"Text": "It's okay, nothing special."},
    {"Text": "The customer service was fantastic and very helpful!"}
]

# Analyze sentiment
sentiments = analyze_text_dict(data)

# Display results
print("Sentiment Analysis Results:")
print("-" * 50)
for i, item in enumerate(data):
    print(f"Text: {item['Text'][:50]}...")
    print(f"Sentiment: {sentiments[i]}")
    print("-" * 50)

# You can also analyze a single item
single_item = [{"Text": "example text here"}]
result = analyze_text_dict(single_item)
print(f"\nSingle analysis result: {result[0]}")
