from __future__ import annotations

import threading

from django.core.cache import cache

from services.recommendation_engine_service import RecommendationEngineService
from utils.cache_keys import recommendation_key


def refresh_recommendation_cache(user_id: int, *, ttl_seconds: int = 60 * 5) -> None:
    payload = RecommendationEngineService().recommend(user_id=user_id)
    try:
        from assessment.services.counsellor_report_service import (
            build_counsellor_report,
        )

        report = build_counsellor_report(payload)
        if report:
            payload["report"] = report
    except Exception:
        pass
    cache.set(recommendation_key(user_id), payload, ttl_seconds)


def refresh_recommendation_cache_async(
    user_id: int, *, ttl_seconds: int = 60 * 5
) -> None:
    """Best-effort async cache refresh using a daemon thread."""
    lock_key = f"{recommendation_key(user_id)}:refresh_lock"
    try:
        got_lock = cache.add(lock_key, 1, 30)
    except Exception:
        got_lock = True

    if not got_lock:
        return

    def _run():
        try:
            refresh_recommendation_cache(user_id, ttl_seconds=ttl_seconds)
        except Exception:
            return
        finally:
            try:
                cache.delete(lock_key)
            except Exception:
                pass

    threading.Thread(target=_run, name=f"rec-refresh-{user_id}", daemon=True).start()
