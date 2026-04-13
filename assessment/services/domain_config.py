"""
Domain scoring configuration — DB-driven.
get_domain_config() loads from DomainScoringConfig, falls back to _FALLBACK_DOMAIN_CONFIG
only if no DB record exists (e.g. before init_data is run).
"""

from __future__ import annotations

# ── Emergency fallback config ─────────────────────────────────────────────────
# Used ONLY when DomainScoringConfig has no record for a domain (e.g. fresh DB before init_data).
# This is a safety net — the real config lives in the DB and is loaded via init_data.
# Do NOT add new domains here; add them to core/management/source/domain_scoring_config.csv instead.
_FALLBACK_DOMAIN_CONFIG: dict[str, dict] = {
    "sports": {
        "dimensions": {
            "interest": 0.30,
            "aptitude": 0.30,
            "personality": 0.20,
            "work_style": 0.20,
        },
        "careers": {
            "athlete": {
                "dimension_factors": {
                    "interest": 1.00,
                    "aptitude": 1.00,
                    "personality": 0.85,
                    "work_style": 0.90,
                }
            },
            "sports_science": {
                "dimension_factors": {
                    "interest": 0.90,
                    "aptitude": 0.95,
                    "personality": 0.95,
                    "work_style": 1.00,
                }
            },
            "coach": {
                "dimension_factors": {
                    "interest": 0.95,
                    "aptitude": 0.80,
                    "personality": 1.00,
                    "work_style": 0.95,
                }
            },
        },
        "rules": {
            "thresholds": [
                {
                    "dimension": "aptitude",
                    "operator": "lt",
                    "value": 45,
                    "actions": [
                        {"type": "multiply", "career": "athlete", "value": 0.75}
                    ],
                }
            ],
            "suppressions": [
                {
                    "dimension": "interest",
                    "operator": "lt",
                    "value": 40,
                    "careers": {"athlete": 0.40, "sports_science": 0.70, "coach": 0.55},
                }
            ],
            "hybrid_margin": 5,
        },
        "defaults": {"missing_dimension_score": 50.0, "max_score_per_answer": 5.0},
    }
}


def get_domain_config(domain_code: str) -> dict | None:
    key = (domain_code or "").strip().lower()
    if not key:
        return None
    try:
        from domain.models import DomainScoringConfig

        obj = DomainScoringConfig.objects.filter(
            domain_code=key, is_active=True
        ).first()
        if obj and obj.config:
            return obj.config
    except Exception:
        pass
    return _FALLBACK_DOMAIN_CONFIG.get(key)


def domain_has_config(domain_code: str) -> bool:
    return get_domain_config(domain_code) is not None


class _LazyDomainConfig:
    def __contains__(self, key: str) -> bool:
        return domain_has_config(key)

    def __getitem__(self, key: str) -> dict:
        cfg = get_domain_config(key)
        if cfg is None:
            raise KeyError(key)
        return cfg

    def get(self, key: str, default=None):
        return get_domain_config(key) or default


DOMAIN_CONFIG = _LazyDomainConfig()
