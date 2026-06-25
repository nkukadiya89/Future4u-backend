class CourseGenerationError(Exception):
    """Base error for AI course generation flow."""


class CourseGenerationAccessDeniedError(CourseGenerationError):
    pass


class CourseGenerationConfigurationError(CourseGenerationError):
    pass


class CourseGenerationValidationError(CourseGenerationError):
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
