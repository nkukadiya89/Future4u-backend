import json
import logging
import time

from django.conf import settings

logger = logging.getLogger("future4u.api")


class APILatencyLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        if request.path.startswith("/api/"):
            payload = {
                "event": "api_request",
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "duration_target_ms": settings.API_RESPONSE_TARGET_MS,
                "target_exceeded": duration_ms > settings.API_RESPONSE_TARGET_MS,
            }
            logger.info(json.dumps(payload))
        return response
