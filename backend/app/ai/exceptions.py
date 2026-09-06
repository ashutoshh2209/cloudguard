class AIError(Exception):
    """Base class for all AI related exceptions."""
    pass

class AIProviderUnavailableError(AIError):
    """Raised when the AI provider cannot be reached or is disabled."""
    pass

class AIAnalysisTimeoutError(AIError):
    """Raised when the AI analysis takes too long."""
    pass

class AIRateLimitError(AIError):
    """Raised when the AI provider rate limit is exceeded."""
    pass

class AIResponseFormatError(AIError):
    """Raised when the AI provider returns a response in an invalid format."""
    pass
