from __future__ import annotations

import os

from django.conf import settings

_CONFIGURED = False


def configure_langsmith() -> None:
    """Apply LangSmith tracing env vars once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    tracing = str(getattr(settings, "LANGCHAIN_TRACING_V2", "false")).lower() in (
        "1",
        "true",
        "yes",
    )
    if tracing:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        api_key = getattr(settings, "LANGCHAIN_API_KEY", "") or ""
        if api_key:
            os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGCHAIN_PROJECT"] = getattr(
            settings, "LANGCHAIN_PROJECT", "future4u"
        )

    _CONFIGURED = True
