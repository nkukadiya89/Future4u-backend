class JobGenerationError(Exception):
    """Base error for AI job generation flow."""


class JobGenerationAccessDeniedError(JobGenerationError):
    pass


class JobGenerationConfigurationError(JobGenerationError):
    pass


class JobGenerationValidationError(JobGenerationError):
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
