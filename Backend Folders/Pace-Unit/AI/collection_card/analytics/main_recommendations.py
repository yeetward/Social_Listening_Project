import argparse
import generate_recommendations
import fetch_user_history
import json
import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate personalized recommendations based on search history."
    )
    parser.add_argument(
        "--type",
        type=str,
        default="research_topics",
        choices=["research_topics", "trends", "connections", "deep_dive"],
        help="Type of recommendations to generate",
    )
    parser.add_argument(
        "--search-limit",
        type=int,
        default=5,
        help="Number of recent searches to analyze (default: 5)",
    )
    parser.add_argument(
        "--articles-per-search",
        type=int,
        default=10,
        help="Number of top articles per search (default: 10)",
    )
    parser.add_argument("--verbose", action="store_true", help="Show debug output")
    args = parser.parse_args()

    def log(message):
        if args.verbose:
            print(message, file=sys.stderr)

    try:
        # Build interest profile from recent histories
        log(f"Fetching last {args.search_limit} search histories...")
        profile = fetch_user_history.build_interest_profile(
            search_limit=args.search_limit,
            articles_per_history=args.articles_per_search,
        )

        num_histories = len(profile["search_history"])
        total_articles = sum(len(h["top_articles"]) for h in profile["search_history"])

        log(f"Analyzed {num_histories} histories with {total_articles} articles")

        # Generate recommendations
        log(f"Generating {args.type} recommendations...")
        recommendations = generate_recommendations.generate_personalized_ideas(
            profile, idea_type=args.type
        )

        log(f"Generated {len(recommendations)} recommendations")

        # Output clean JSON to stdout
        print(json.dumps(recommendations, indent=2))

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
