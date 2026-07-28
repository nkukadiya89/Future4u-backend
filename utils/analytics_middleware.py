from __future__ import annotations

import json
import logging
import time

logger = logging.getLogger("api.analytics")


class ApiAnalyticsMiddleware:
    """
    Lightweight request/response analytics.
    Disabled unless enabled in settings (see future4u/settings.py).

    Emits one structured log line per request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        try:
            duration_ms = int((time.perf_counter() - start) * 1000)
            user = getattr(request, "user", None)
            payload = {
                "path": getattr(request, "path", None),
                "method": getattr(request, "method", None),
                "status_code": getattr(response, "status_code", None),
                "duration_ms": duration_ms,
                "user_id": (
                    getattr(user, "id", None)
                    if getattr(user, "is_authenticated", False)
                    else None
                ),
                "ip": request.META.get("REMOTE_ADDR"),
                "ua": request.META.get("HTTP_USER_AGENT"),
            }
            logger.info(json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass
        return response
