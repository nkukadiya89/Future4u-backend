try:
    from future4u.celery import app as celery_app
except Exception:  # pragma: no cover - optional local dependency
    celery_app = None

__all__ = ("celery_app",)
