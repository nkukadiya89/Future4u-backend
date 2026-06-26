class InternshipGenerationError(Exception):
    """Base error for AI internship generation flow."""


class InternshipGenerationAccessDeniedError(InternshipGenerationError):
    pass


class InternshipGenerationConfigurationError(InternshipGenerationError):
    pass


class InternshipGenerationValidationError(InternshipGenerationError):
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
