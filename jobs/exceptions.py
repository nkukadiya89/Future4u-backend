"""
Custom exceptions for the LinkedIn Job Search integration.

Hierarchy:
  LinkedInJobServiceError (base)
  ├── LinkedInJobAPIAuthError       (401/403)
  ├── LinkedInJobAPIRateLimitError  (429)
  ├── LinkedInJobAPITimeoutError    (timeout)
  ├── LinkedInJobAPIError           (other HTTP / connection errors)
  └── LinkedInJobValidationError    (input / response validation)
"""


class LinkedInJobServiceError(Exception):
    """Base exception for the LinkedIn Job Search service."""


class LinkedInJobAPIAuthError(LinkedInJobServiceError):
    """Raised when the external API returns 401 Unauthorized or 403 Forbidden."""


class LinkedInJobAPIRateLimitError(LinkedInJobServiceError):
    """Raised when the external API returns 429 Too Many Requests."""


class LinkedInJobAPITimeoutError(LinkedInJobServiceError):
    """Raised when the request to the external API times out."""


class LinkedInJobAPIError(LinkedInJobServiceError):
    """Raised for other HTTP or connection-level errors from the external API."""


class LinkedInJobValidationError(LinkedInJobServiceError):
    """Raised when user input or the external API response fails validation."""
