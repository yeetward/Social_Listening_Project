# # AI/ML/competitor_fusion_demo.py
# from .competitor_fusion import rank_competitors_fused

# sample = """
# Apple Inc. is facing increasing competition from Samsung and Google in the smartphone market.
# Tim Cook, Apple's CEO, mentioned innovation will drive iPhone strategy this year.
# Meanwhile, Microsoft is expanding cloud services, competing with Amazon Web Services and Google Cloud.
# """


# def run(
#     text: str,
#     seed_brand: str,
#     industry: list[str] | None = None,
#     location: list[str] | None = None,
#     top_n: int = 5,
#     min_score: float = 0.25,
#     verbose: bool = False,
# ):
#     """
#     Wrapper entry point to call rank_competitors_fused() and return structured results.
#     """
#     try:
#         results = rank_competitors_fused(
#             text=text,
#             seed_brand=seed_brand,
#             industry=industry or [],
#             location=location or [],
#             top_n=top_n,
#             min_score=min_score,
#         )

#         if verbose:
#             print(f"✓ Generated {len(results)} competitor candidates")
#             for r in results:
#                 print(f"{r['name']:25s}  score={r['score']:.3f}  -> {r['explanation']}")

#         return results

#     except Exception as e:
#         raise RuntimeError(f"competitor_fusion_demo.run() failed: {e}")


# if __name__ == "__main__":
#     results = rank_competitors_fused(
#         text=sample,
#         seed_brand="Apple",
#         industry=["smartphone", "mobile", "device", "cloud"],
#         location=["US", "United States"],
#         top_n=5,
#         min_score=0.25,
#     )
#     for r in results:
#         print(f"{r['name']:20s}  score={r['score']:.3f}  -> {r['explanation']}")
