class ProjectRecommendationError(Exception):
    """Base error for AI project recommendation flow."""


class ProjectRecommendationAccessDeniedError(ProjectRecommendationError):
    pass


class ProjectRecommendationConfigurationError(ProjectRecommendationError):
    pass


class ProjectRecommendationValidationError(ProjectRecommendationError):
    def __init__(
        self,
        message: str,
        *,
        error: str = "Validation failed",
        details: str | None = None,
    ):
        super().__init__(message)
        self.error = error
        self.details = details or message
