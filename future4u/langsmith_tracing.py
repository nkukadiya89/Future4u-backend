"""LangSmith env bootstrap only — does not change LLM prompts, models, or API responses."""

from __future__ import annotations

import os


def apply_langsmith_tracing_env(
    *,
    enabled: bool,
    api_key: str = "",
    project: str = "future4u",
) -> None:
    if not enabled:
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING_V2"] = "true"

    if api_key:
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGSMITH_API_KEY"] = api_key

    project_name = (project or "future4u").strip() or "future4u"
    os.environ["LANGCHAIN_PROJECT"] = project_name
    os.environ["LANGSMITH_PROJECT"] = project_name

    try:
        from langsmith.utils import get_env_var

        get_env_var.cache_clear()
    except Exception:
        pass
