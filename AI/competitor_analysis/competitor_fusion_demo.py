# AI/ML/competitor_fusion_demo.py
from AI.ML.competitor_fusion import rank_competitors_fused

sample = """
Apple Inc. is facing increasing competition from Samsung and Google in the smartphone market.
Tim Cook, Apple's CEO, mentioned innovation will drive iPhone strategy this year.
Meanwhile, Microsoft is expanding cloud services, competing with Amazon Web Services and Google Cloud.
"""

if __name__ == "__main__":
    results = rank_competitors_fused(
        text=sample,
        seed_brand="Apple",
        industry=["smartphone", "mobile", "device", "cloud"],
        location=["US", "United States"],
        top_n=5,
        min_score=0.25,
    )
    for r in results:
        print(f"{r['name']:20s}  score={r['score']:.3f}  -> {r['explanation']}")
