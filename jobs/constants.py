"""
Constants and configuration defaults for the LinkedIn Job Search integration.
"""

# ── External API ──────────────────────────────────────────────────────────────
DEFAULT_API_BASE_URL: str = "https://linkedin-job-search-api.p.rapidapi.com"
DEFAULT_SEARCH_ENDPOINT: str = "/active-jb"

# ── HTTP / Network ────────────────────────────────────────────────────────────
REQUEST_TIMEOUT_SECONDS: int = 15       # per‑request timeout
MAX_RETRIES: int = 2                    # how many times to retry on failure
RETRYABLE_STATUSES: set[int] = {429, 500, 502, 503, 504}

# ── Caching ───────────────────────────────────────────────────────────────────
CACHE_TTL_SECONDS: int = 3600           # 1 hour
CACHE_KEY_PREFIX: str = "jobs:search"

# ── Pagination ────────────────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE: int = 10
MAX_PAGE_SIZE: int = 50

# ── Feature toggle ────────────────────────────────────────────────────────────
# This can be overridden in Django settings via JOBS_LINKEDIN_SEARCH_ENABLED
LINKEDIN_SEARCH_ENABLED: bool = True

# ── Allowed filter keys passed to the external API ────────────────────────────
# Maps our user‑friendly query params to the external API parameter names.
# Only params the /active-jb endpoint actually supports are included.
# Unsupported filters (country, city, state, remote, salary, etc.) are
# handled via post‑processing in _filter_results().
API_PARAM_MAP: dict[str, str] = {
    "title": "title",
    "location": "location",
    "posted_within": "time_frame",
    "limit": "limit",
}

# ── Filters applied locally (post-processing) ────────────────────────────────
# These params are NOT sent to the external API but are applied server-side
# to filter results after fetching.
LOCAL_FILTER_KEYS: set[str] = {
    "country",
    "state",
    "city",
    "remote",
    "hybrid",
    "employment_type",
    "experience_level",
    "salary_min",
    "salary_max",
    "company",
}

# Default value for the required time_frame parameter (used when user
# does not pass posted_within).
DEFAULT_TIME_FRAME: str = "7d"
