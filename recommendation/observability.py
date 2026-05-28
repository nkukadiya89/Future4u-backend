from __future__ import annotations

import os

from django.conf import settings

_CONFIGURED = False


def configure_langsmith_tracing() -> None:
    """Enable LangSmith tracing only when explicitly configured."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    tracing_enabled = str(
        getattr(settings, "AI_TRACING_ENABLED", "false")
    ).strip().lower() in ("1", "true", "yes")
    if tracing_enabled:
        # LangSmith tracing is controlled by LangChain's standard env vars.
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        api_key = getattr(settings, "LANGSMITH_API_KEY", "") or ""
        if api_key:
            os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGCHAIN_PROJECT"] = getattr(
            settings,
            "LANGSMITH_PROJECT",
            "future4u",
        )

    _CONFIGURED = True
