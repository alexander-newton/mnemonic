"""Custom exception hierarchy for Mnemonic.

All exceptions in Mnemonic must inherit from MnemonicError. This ensures:
- Clear error boundaries between application and external libraries
- Consistent error handling in middleware
- Informative error messages that never fail silently
"""


class MnemonicError(Exception):
    """Base exception for all Mnemonic errors."""

    pass


# Database errors
class NotFoundError(MnemonicError):
    """Resource not found."""

    pass


class CardNotFoundError(NotFoundError):
    """Card not found."""

    pass


class DeckNotFoundError(NotFoundError):
    """Deck not found."""

    pass


# Validation errors
class ValidationError(MnemonicError):
    """Invalid input data."""

    pass


class InvalidRatingError(ValidationError):
    """Invalid review rating."""

    pass


class InvalidCardSyntaxError(ValidationError):
    """Invalid card syntax."""

    pass


# LLM errors
class LLMError(MnemonicError):
    """Base class for LLM-related errors."""

    pass


class LLMConfigError(LLMError):
    """LLM configuration issue (API key, model selection)."""

    pass


class LLMRateLimitError(LLMError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: int) -> None:
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
        """
        super().__init__(message)
        self.retry_after = retry_after


class LLMUnavailableError(LLMError):
    """LLM service unavailable."""

    pass


# Rendering errors
class RenderError(MnemonicError):
    """Card rendering failed."""

    pass


class PandocError(RenderError):
    """Pandoc rendering failed."""

    pass


class MathJaxError(RenderError):
    """MathJax rendering failed."""

    pass
