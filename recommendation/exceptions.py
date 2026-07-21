class AIRecommendationError(Exception):
    """Base error for AI recommendation flow."""


class AssessmentNotFoundError(AIRecommendationError):
    pass


class AssessmentAccessDeniedError(AIRecommendationError):
    pass


class AssessmentNotReadyError(AIRecommendationError):
    pass


class AIConfigurationError(AIRecommendationError):
    pass


class AIGenerationError(AIRecommendationError):
    pass

