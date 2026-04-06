from __future__ import annotations

import threading
from typing import Any

from django.core.cache import cache

from services.recommendation_engine_service import generate_recommendation
from utils.cache_keys import recommendation_key


def _compute_payload(user_id: int) -> dict[str, Any]:
    out = generate_recommendation(user_id)
    return {
        "message": out.get("message") or "ok",
        "suggestion": out.get("suggestion") or [],
        "top_domains": out.get("top_domains") or [],
        "top_careers": out.get("top_careers") or [],
        "skill_gaps": out.get("skill_gaps") or [],
    }


def refresh_recommendation_cache(user_id: int, *, ttl_seconds: int = 60 * 5) -> None:
    payload = _compute_payload(user_id)
    cache.set(recommendation_key(user_id), payload, ttl_seconds)


def refresh_recommendation_cache_async(
    user_id: int, *, ttl_seconds: int = 60 * 5
) -> None:
    """
    Best-effort async refresh without requiring Celery.
    Uses a daemon thread and a cache lock to avoid stampedes.
    """

    lock_key = f"{recommendation_key(user_id)}:refresh_lock"
    try:
        got_lock = cache.add(lock_key, 1, 30)  # 30s lock
    except Exception:
        got_lock = True

    if not got_lock:
        return

    def _run():
        try:
            refresh_recommendation_cache(user_id, ttl_seconds=ttl_seconds)
        except Exception:
            # Never raise from background job
            return
        finally:
            try:
                cache.delete(lock_key)
            except Exception:
                pass

    t = threading.Thread(target=_run, name=f"rec-refresh-{user_id}", daemon=True)
    t.start()
