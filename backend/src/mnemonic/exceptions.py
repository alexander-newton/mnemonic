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


# Integrity errors
class IntegrityError(MnemonicError):
    """Card content integrity check failed (e.g. an un-hashable empty core)."""

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


# LLM additions
class LLMBudgetExceededError(LLMError):
    """LLM cost cap (daily or monthly) reached."""

    def __init__(self, spent_millicents: int, cap_millicents: int, scope: str) -> None:
        """Initialize budget exceeded error.

        Args:
            spent_millicents: Amount spent in millicents (1/100th of a cent)
            cap_millicents: Budget cap in millicents
            scope: Budget scope (e.g., "daily", "monthly")
        """
        self.spent_millicents = spent_millicents
        self.cap_millicents = cap_millicents
        self.scope = scope
        super().__init__(
            f"LLM {scope} budget exceeded: spent "
            f"{spent_millicents / 1000:.2f} cents of {cap_millicents / 1000:.2f} cents. "
            f"Raise the cap in [llm.budget] in ~/.config/mnemonic/config.toml."
        )


# Git errors
class GitError(MnemonicError):
    """Base class for Git operation failures."""

    pass


class GitDirtyWorkingTreeError(GitError):
    """Vault has uncommitted changes; refuse to start a session."""

    pass


class GitNonFastForwardError(GitError):
    """Remote has commits that cannot fast-forward into local."""

    pass


class GitPushRejectedError(GitError):
    """Push rejected by remote (typically: concurrent push)."""

    pass


# Vault errors
class VaultError(MnemonicError):
    """Base class for vault-layer failures."""

    pass


class VaultNotConfiguredError(VaultError):
    """vault_path missing and no vault_remote available to clone."""

    pass


class MalformedNoteError(VaultError):
    """A card-note does not match the canonical structure."""

    pass


class MalformedVariationSectionError(VaultError):
    """## Variations section is missing the begin/end markers."""

    pass


class OrphanCardError(VaultError):
    """A SchedulingState row has no corresponding card-note."""

    pass


# Optimization errors
class OptimizationError(MnemonicError):
    """Base class for prompt-optimization failures."""

    pass


class InsufficientDataError(OptimizationError):
    """Not enough labeled examples to perform an optimization step."""

    def __init__(self, strategy: str, have: int, need: int) -> None:
        """Initialize insufficient-data error.

        Args:
            strategy: The strategy whose trainset is too small.
            have: Number of usable examples currently available.
            need: Minimum number of examples required.
        """
        self.strategy = strategy
        self.have = have
        self.need = need
        super().__init__(
            f"Not enough labeled examples for strategy '{strategy}': "
            f"have {have}, need {need}. Keep reviewing to accumulate more, "
            "or lower min_examples_to_compile in [optimization] config."
        )
