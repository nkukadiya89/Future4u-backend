from __future__ import annotations

__all__ = ["RecommendationPipeline"]


def __getattr__(name: str):
    if name == "RecommendationPipeline":
        from services.ai.pipeline.recommendation_pipeline import RecommendationPipeline

        return RecommendationPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
