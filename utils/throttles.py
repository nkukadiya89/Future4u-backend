from __future__ import annotations

from rest_framework.throttling import SimpleRateThrottle


class PerUserBurstRateThrottle(SimpleRateThrottle):
    """
    View-level throttle with an explicit, code-defined rate.
    Safe to add without changing global REST_FRAMEWORK settings.
    """

    scope = "user_burst"
    rate = "30/min"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            ident = self.get_ident(request)
            return f"throttle:{self.scope}:ip:{ident}"
        return f"throttle:{self.scope}:user:{request.user.pk}"


class PerUserSustainedRateThrottle(PerUserBurstRateThrottle):
    scope = "user_sustained"
    rate = "300/hour"


class RecommendationRateThrottle(PerUserBurstRateThrottle):
    scope = "recommendation"
    rate = "10/min"

