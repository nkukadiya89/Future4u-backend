"""
Service layer for the LinkedIn Job Search integration.

LinkedInJobService is the central class responsible for:
- Calling the external RapidAPI endpoint
- Handling authentication headers, query parameters, and pagination
- Implementing request timeouts and retry logic
- Caching identical searches
- Validating and normalising responses
- Logging failures without leaking credentials
"""

from __future__ import annotations

import copy
import logging
import time
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache

from jobs.constants import (
    API_PARAM_MAP,
    CACHE_KEY_PREFIX,
    CACHE_TTL_SECONDS,
    DEFAULT_API_BASE_URL,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SEARCH_ENDPOINT,
    DEFAULT_TIME_FRAME,
    LOCAL_FILTER_KEYS,
    MAX_PAGE_SIZE,
    MAX_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    RETRYABLE_STATUSES,
)
from jobs.exceptions import (
    LinkedInJobAPIAuthError,
    LinkedInJobAPIError,
    LinkedInJobAPIRateLimitError,
    LinkedInJobAPITimeoutError,
    LinkedInJobServiceError,
    LinkedInJobValidationError,
)
from jobs.serializers import JobNormalizedSerializer

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
#  Feature toggle
# ──────────────────────────────────────────────────────────────────────────────


def linkedin_search_enabled() -> bool:
    """Return whether the LinkedIn Job Search feature is enabled."""
    return getattr(settings, "JOBS_LINKEDIN_SEARCH_ENABLED", True)


# ──────────────────────────────────────────────────────────────────────────────
#  Credentials helper
# ──────────────────────────────────────────────────────────────────────────────


def _get_api_key() -> str:
    """Return the RapidAPI key from Django settings.

    Raises LinkedInJobServiceError if the key is not configured.
    """
    key = getattr(settings, "RAPIDAPI_KEY", "").strip()
    if not key:
        raise LinkedInJobServiceError(
            "LinkedIn Job Search is not configured. Please set RAPIDAPI_KEY."
        )
    return key


def _get_api_host() -> str:
    """Return the RapidAPI host from Django settings."""
    host = getattr(
        settings, "RAPIDAPI_HOST", "linkedin-job-search-api.p.rapidapi.com"
    ).strip()
    return host


def _get_api_base_url() -> str:
    """Return the API base URL from settings or the default."""
    return getattr(settings, "RAPIDAPI_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")


# ──────────────────────────────────────────────────────────────────────────────
#  Service
# ──────────────────────────────────────────────────────────────────────────────


class LinkedInJobService:
    """
    Service for searching jobs via the LinkedIn Job Search (RapidAPI) API.

    Usage::

        service = LinkedInJobService()
        result = service.search_jobs({"title": "Python Developer", "location": "Ahmedabad"})
    """

    def __init__(self) -> None:
        self._session: requests.Session | None = None
        self._base_url = _get_api_base_url()

    # ── Public API ──────────────────────────────────────────────────────────

    def search_jobs(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Search for jobs using the external LinkedIn API.

        ``params`` should already be validated by ``JobSearchQuerySerializer``.

        Returns a dictionary with the keys:
            - success (bool)
            - count (int)
            - data (list[dict])
            - page (int)
            - total_pages (int | None)
            - message (str)
        """
        if not linkedin_search_enabled():
            return {
                "success": False,
                "message": "LinkedIn Job Search is currently disabled.",
                "count": 0,
                "data": [],
                "page": params.get("page", 1),
                "total_pages": None,
            }

        # Clamp pagination
        page = max(1, int(params.get("page", 1)))
        limit = max(1, min(int(params.get("limit", DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE))

        title = (params.get("title") or "").strip()
        location = (params.get("location") or "").strip()

        cache_key = self._build_cache_key(title, location, page)

        # Try cache first
        cached = cache.get(cache_key)

        if cached is not None:
            logger.info("LinkedIn job search cache HIT for key=%s", cache_key)
            # Apply local filters on cached results too
            filtered = self._filter_results(cached, params)
            return filtered

        logger.info("LinkedIn job search cache MISS for key=%s", cache_key)

        # Build external API params (only supported params, skip local filters)
        api_params = self._build_api_params(params, limit=limit, page=page)

        try:
            raw_data = self._call_api(api_params)
        except LinkedInJobServiceError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error during LinkedIn job search")
            raise LinkedInJobAPIError(f"Unexpected error: {exc}") from exc

        # Normalise the response (unfiltered — cache this for reuse)
        result = self._normalize_response(raw_data, page=page)

        # Cache the unfiltered result
        cache.set(cache_key, result, CACHE_TTL_SECONDS)

        # Apply local filters and return
        filtered = self._filter_results(result, params)
        return filtered

    # ── Cache helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _build_cache_key(title: str, location: str, page: int) -> str:
        """Build a deterministic cache key for a given search."""
        # Normalise to avoid cache misses due to casing / extra spaces
        title_part = title.lower().strip() if title else ""
        location_part = location.lower().strip() if location else ""
        return f"{CACHE_KEY_PREFIX}:{title_part}:{location_part}:{page}"

    # ── API call ────────────────────────────────────────────────────────────

    def _get_session(self) -> requests.Session:
        """Return a reusable requests Session (connection pooling)."""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _build_api_params(
        self,
        params: dict[str, Any],
        *,
        limit: int,
        page: int,
    ) -> dict[str, str]:
        """
        Map our internal parameter names to the external API's parameter names.

        Only params in ``API_PARAM_MAP`` are sent (supported by /active-jb).
        Filters like country, city, remote, salary, etc. are handled via
        post‑processing in ``_filter_results()``.

        The external API uses ``limit`` and ``offset`` for pagination
        (not ``page``), so we calculate offset = (page - 1) * limit.

        Only non‑empty / non‑None values are included.
        """
        api_params: dict[str, str] = {
            "limit": str(limit),
            "offset": str((page - 1) * limit),
            # The /active-jb endpoint requires a time_frame parameter.
            "time_frame": DEFAULT_TIME_FRAME,
        }
        for our_key, api_key in API_PARAM_MAP.items():
            value = params.get(our_key)
            if value is None or value == "" or value is False:
                continue
            api_params[api_key] = str(value)

        return api_params

    def _call_api(self, params: dict[str, str]) -> dict[str, Any]:
        """
        Make the HTTP request to the external API with retry logic.

        Raises specialised exceptions for auth errors, rate limits, timeouts,
        and general API failures.
        """
        api_key = _get_api_key()
        api_host = _get_api_host()
        endpoint = f"{self._base_url}{DEFAULT_SEARCH_ENDPOINT}"

        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": api_host,
        }

        session = self._get_session()
        last_exception: Exception | None = None

        for attempt in range(1 + MAX_RETRIES):
            start_time = time.monotonic()
            try:
                response = session.get(
                    endpoint,
                    headers=headers,
                    params=params,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                duration = time.monotonic() - start_time
                logger.info(
                    "LinkedIn API request completed in %.2fs (attempt %d/%d) "
                    "status=%s params=%s",
                    duration,
                    attempt + 1,
                    1 + MAX_RETRIES,
                    response.status_code,
                    params,
                )

                if response.status_code in (401, 403):
                    raise LinkedInJobAPIAuthError(
                        "LinkedIn Job Search API authentication failed. "
                        "Please check your RAPIDAPI_KEY."
                    )
                if response.status_code == 404:
                    logger.warning(
                        "LinkedIn API returned 404 for endpoint=%s params=%s — "
                        "the API endpoint may be incorrect or the resource does not exist.",
                        endpoint,
                        params,
                    )
                    return {"data": [], "total": 0}
                if 400 <= response.status_code < 500 and response.status_code not in (
                    401,
                    403,
                    404,
                    429,
                ):
                    # 400/422 — bad request (invalid params). Log the response body and return empty.
                    try:
                        body = response.text[:500]
                    except Exception:
                        body = "<unreadable>"
                    logger.warning(
                        "LinkedIn API returned %d for endpoint=%s params=%s — "
                        "body=%s",
                        response.status_code,
                        endpoint,
                        params,
                        body,
                    )
                    return {"data": [], "total": 0}
                if response.status_code in RETRYABLE_STATUSES:
                    if attempt < MAX_RETRIES:
                        logger.warning(
                            "LinkedIn API returned %d, retrying (attempt %d/%d)",
                            response.status_code,
                            attempt + 2,
                            1 + MAX_RETRIES,
                        )
                        time.sleep(1 * (attempt + 1))  # linear back-off
                        continue
                    if response.status_code == 429:
                        raise LinkedInJobAPIRateLimitError(
                            "LinkedIn Job Search API rate limit exceeded. "
                            "Please try again later."
                        )
                    raise LinkedInJobAPIError(
                        f"LinkedIn Job Search API returned status {response.status_code}."
                    )

                response.raise_for_status()
                return response.json()

            except requests.Timeout as exc:
                duration = time.monotonic() - start_time
                logger.warning(
                    "LinkedIn API request timed out after %.2fs (attempt %d/%d)",
                    duration,
                    attempt + 1,
                    1 + MAX_RETRIES,
                )
                last_exception = exc
                if attempt < MAX_RETRIES:
                    time.sleep(1 * (attempt + 1))
                    continue
                raise LinkedInJobAPITimeoutError(
                    "LinkedIn Job Search API request timed out. "
                    "Please try again later."
                ) from exc

            except requests.ConnectionError as exc:
                logger.warning(
                    "LinkedIn API connection error (attempt %d/%d): %s",
                    attempt + 1,
                    1 + MAX_RETRIES,
                    exc,
                )
                last_exception = exc
                if attempt < MAX_RETRIES:
                    time.sleep(1 * (attempt + 1))
                    continue
                raise LinkedInJobAPIError(
                    "Unable to connect to LinkedIn Job Search API. "
                    "Please check your network connection."
                ) from exc

        # Should not reach here, but just in case
        raise LinkedInJobAPIError(
            "LinkedIn Job Search API request failed after retries."
        ) from last_exception

    # ── Response normalisation ─────────────────────────────────────────────

    def _normalize_response(
        self,
        raw_data: Any,
        *,
        page: int,
    ) -> dict[str, Any]:
        """
        Convert the raw external API response into Future4u's standard format.

        Handles both dict and list response shapes to be resilient to API changes.
        """
        # Handle case where the response itself is a top-level list
        if isinstance(raw_data, list):
            raw_results = raw_data
            raw_data = {}  # ensure raw_data is a dict for total/total_pages lookup
        elif isinstance(raw_data, dict):
            # The API may return results under 'data', 'results', or 'jobs'
            raw_results = (
                raw_data.get("data")
                or raw_data.get("results")
                or raw_data.get("jobs")
                or []
            )
        else:
            raw_results = []
            raw_data = {}

        if not isinstance(raw_results, list):
            raw_results = []

        normalized_jobs = []

        for raw_job in raw_results:
            if not isinstance(raw_job, dict):
                continue
            mapped = self._map_raw_job(raw_job)
            serializer = JobNormalizedSerializer(data=mapped)
            if serializer.is_valid():
                normalized_jobs.append(serializer.data)
            else:
                logger.warning(
                    "Skipping job due to normalisation error: %s",
                    serializer.errors,
                )

        total = (
            raw_data.get("total") or raw_data.get("total_count") or len(normalized_jobs)
        )
        total_pages = raw_data.get("total_pages")
        if total_pages is None and isinstance(total, int) and total > 0:
            limit = self._guess_limit(normalized_jobs)
            total_pages = max(1, (total + limit - 1) // limit) if limit else 1

        return {
            "success": True,
            "count": len(normalized_jobs),
            "data": normalized_jobs,
            "page": page,
            "total_pages": total_pages,
            "message": "Jobs fetched successfully.",
        }

    @staticmethod
    def _map_raw_job(raw: dict) -> dict:
        """
        Map raw API job fields into Future4u's standard normalised format.

        The /active-jb endpoint returns jobs with these fields:
        id, title, organization, organization_logo, locations, location_type,
        salary, employment_type (list), seniority, date_posted, url,
        cities_derived (list), regions_derived (list),
        countries_derived (list), source, source_type, org_linkedin_url, etc.

        Missing or null values get safe defaults.
        """
        # ── Simple string fields ───────────────────────────────────────
        result = {
            "id": str(raw.get("id") or raw.get("linkedin_id") or ""),
            "title": raw.get("title") or "",
            "company": raw.get("organization") or "",
            "company_logo": raw.get("organization_logo") or "",
            "location": "",
            "country": "",
            "city": "",
            "state": "",
            "employment_type": "",
            "experience_level": raw.get("experience_level") or "",
            "salary_min": None,
            "salary_max": None,
            "currency": "INR",
            "remote_type": raw.get("location_type") or "",
            "description": raw.get("description") or raw.get("job_description") or "",
            "skills": raw.get("skills") or [],
            "posted_at": raw.get("date_posted") or "",
            "apply_url": raw.get("url") or "",
            "source": "linkedin",
            "company_size": "",
            "industry": raw.get("industry") or "",
            "seniority": raw.get("seniority") or "",
            "job_url": raw.get("url") or "",
        }

        # ── locations (list of LinkedIn Place objects) ─────────────────
        # The API returns something like:
        #   [{'@type': 'Place', 'address': {'@type': 'PostalAddress',
        #     'addressLocality': 'España', 'addressRegion': '', ...}}]
        locations = raw.get("locations", [])
        if isinstance(locations, list):
            for loc_item in locations:
                if isinstance(loc_item, dict):
                    address = loc_item.get("address") or {}
                    if isinstance(address, dict):
                        locality = address.get("addressLocality") or ""
                        region = address.get("addressRegion") or ""
                        country_addr = address.get("addressCountry") or ""
                        parts = [p for p in [locality, region, country_addr] if p]
                        if parts:
                            result["location"] = ", ".join(parts)
                            break
                    # fallback: whole item as string
                    if not result["location"]:
                        result["location"] = str(loc_item)
                        break
                elif isinstance(loc_item, str):
                    result["location"] = loc_item
                    break
        elif isinstance(locations, str):
            result["location"] = locations

        # ── Derived location fields (lists from the API) ───────────────
        derived_map = {
            "city": "cities_derived",
            "state": "regions_derived",
            "country": "countries_derived",
        }
        for our_key, api_key in derived_map.items():
            val = raw.get(api_key, [])
            if isinstance(val, list) and val:
                result[our_key] = str(val[0])
            elif isinstance(val, str):
                result[our_key] = val

        # ── employment_type (API returns a list like ["Full-time"]) ────
        emp_type = raw.get("employment_type", [])
        if isinstance(emp_type, list) and emp_type:
            result["employment_type"] = str(emp_type[0])
        elif isinstance(emp_type, str):
            result["employment_type"] = emp_type

        # ── salary (API returns an object) ─────────────────────────────
        salary = raw.get("salary")
        if isinstance(salary, dict):
            result["salary_min"] = _safe_float(salary.get("min_amount"))
            result["salary_max"] = _safe_float(salary.get("max_amount"))
            if salary.get("currency"):
                result["currency"] = salary["currency"]
        elif isinstance(salary, (int, float)):
            result["salary_min"] = _safe_float(salary)

        return result

    @staticmethod
    def _guess_limit(jobs: list[dict]) -> int:
        """Best‑effort guess at the page size for total_pages calculation."""
        if jobs:
            return len(jobs)
        return DEFAULT_PAGE_SIZE

    @staticmethod
    def _filter_results(
        result: dict[str, Any],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Apply local (post‑processing) filters to already‑normalized job results.

        The /active-jb endpoint does not support filters like ``country``,
        ``city``, ``remote``, ``salary_min``, ``employment_type``, etc.
        Those are applied here by inspecting the already‑normalized job dict.

        Returns a new dict — the original ``result`` is not mutated so the
        cache (which stores the object reference) remains pristine.
        """
        jobs = result.get("data", [])
        if not jobs or not any(
            params.get(k)
            for k in LOCAL_FILTER_KEYS
            if params.get(k) is not None and params.get(k) is not False
        ):
            return result  # no local filters to apply

        def _match(job: dict[str, Any]) -> bool:
            """Return True if the job passes all active local filters."""
            # ── country (case‑insensitive substring) ────────────────────
            country_filter = params.get("country")
            if country_filter:
                job_country = (job.get("country") or "").lower()
                if country_filter.lower() not in job_country:
                    return False

            # ── state ─────────────────────────────────────────────────
            state_filter = params.get("state")
            if state_filter:
                job_state = (job.get("state") or "").lower()
                if state_filter.lower() not in job_state:
                    return False

            # ── city ──────────────────────────────────────────────────
            city_filter = params.get("city")
            if city_filter:
                job_city = (job.get("city") or "").lower()
                job_location = (job.get("location") or "").lower()
                needle = city_filter.lower()
                if needle not in job_city and needle not in job_location:
                    return False

            # ── remote ────────────────────────────────────────────────
            remote_filter = params.get("remote")
            if remote_filter is True:
                remote_type = (job.get("remote_type") or "").lower()
                if "remote" not in remote_type and "hybrid" not in remote_type:
                    loc_lower = (job.get("location") or "").lower()
                    if "remote" not in loc_lower:
                        return False

            # ── hybrid ───────────────────────────────────────────────
            hybrid_filter = params.get("hybrid")
            if hybrid_filter is True:
                remote_type = (job.get("remote_type") or "").lower()
                loc_lower = (job.get("location") or "").lower()
                if "hybrid" not in remote_type and "hybrid" not in loc_lower:
                    return False

            # ── employment_type (case‑insensitive) ────────────────────
            emp_filter = params.get("employment_type")
            if emp_filter:
                job_emp = (job.get("employment_type") or "").lower()
                if emp_filter.lower() not in job_emp:
                    return False

            # ── company (case‑insensitive substring) ──────────────────
            company_filter = params.get("company")
            if company_filter:
                job_company = (job.get("company") or "").lower()
                if company_filter.lower() not in job_company:
                    return False

            # ── salary_min ────────────────────────────────────────────
            salary_min_filter = params.get("salary_min")
            if salary_min_filter is not None and salary_min_filter is not False:
                try:
                    job_salary_min = float(job.get("salary_min") or 0)
                    if job_salary_min < float(salary_min_filter):
                        return False
                except (TypeError, ValueError):
                    pass

            # ── salary_max ────────────────────────────────────────────
            salary_max_filter = params.get("salary_max")
            if salary_max_filter is not None and salary_max_filter is not False:
                try:
                    job_salary_max = float(job.get("salary_max") or 0)
                    if job_salary_max > float(salary_max_filter):
                        return False
                except (TypeError, ValueError):
                    pass

            # ── experience_level (case‑insensitive substring) ─────────
            exp_filter = params.get("experience_level")
            if exp_filter:
                job_exp = (job.get("experience_level") or "").lower()
                if exp_filter.lower() not in job_exp:
                    return False

            return True

        # Work on a deep copy so we never corrupt the cache (which stores
        # a reference to the original result dict).
        result_copy = copy.deepcopy(result)
        jobs_copy = result_copy.get("data", [])

        filtered = [job for job in jobs_copy if _match(job)]
        result_copy["data"] = filtered
        result_copy["count"] = len(filtered)

        if result_copy["count"] > 0:
            limit = LinkedInJobService._guess_limit(filtered)
            result_copy["total_pages"] = max(
                1, (result_copy["count"] + limit - 1) // limit
            )
        else:
            result_copy["total_pages"] = 1

        if result_copy["count"] < len(jobs):
            result_copy["message"] = (
                f"Jobs fetched successfully (filtered to {result_copy['count']})."
            )

        return result_copy


def _safe_float(value: Any) -> float | None:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
