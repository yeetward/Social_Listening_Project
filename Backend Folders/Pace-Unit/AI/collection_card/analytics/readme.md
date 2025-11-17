# Generate new research topic ideas based on last 10 searches

python main_recommendations.py --type research_topics --search-limit 10 --verbose

# Identify trends in search behavior

python main_recommendations.py --type trends --search-limit 8 --verbose

# Find connections between different searches

python main_recommendations.py --type connections --verbose

# Suggest deep dive areas with location/industry context

python main_recommendations.py --type deep_dive --search-limit 5 --verbose
