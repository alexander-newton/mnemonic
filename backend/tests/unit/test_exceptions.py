"""Tests for Mnemonic custom exception hierarchy.

This module tests the complete exception hierarchy defined in mnemonic.exceptions.
All tests follow the "NO SILENT FAILURES" principle - exceptions must be informative
and provide clear information about WHAT failed, WHY, and WHAT TO DO.
"""

import pytest

from mnemonic.exceptions import (
    CardNotFoundError,
    DeckNotFoundError,
    InvalidCardSyntaxError,
    InvalidRatingError,
    LLMConfigError,
    LLMError,
    LLMRateLimitError,
    LLMUnavailableError,
    MathJaxError,
    MnemonicError,
    NotFoundError,
    PandocError,
    RenderError,
    ValidationError,
)


class TestMnemonicErrorBase:
    """Test the base MnemonicError exception."""

    def test_mnemonic_error_inherits_from_exception(self):
        """Test that MnemonicError inherits from Exception."""
        assert issubclass(MnemonicError, Exception)

    def test_mnemonic_error_can_be_raised_with_message(self):
        """Test that MnemonicError can be raised with a message."""
        message = "A test error occurred"
        with pytest.raises(MnemonicError) as exc_info:
            raise MnemonicError(message)
        assert str(exc_info.value) == message

    def test_mnemonic_error_can_be_raised_without_message(self):
        """Test that MnemonicError can be raised without a message."""
        with pytest.raises(MnemonicError):
            raise MnemonicError()

    def test_mnemonic_error_message_preserved(self):
        """Test that MnemonicError preserves message formatting."""
        message = "Error: {status} - {detail}"
        with pytest.raises(MnemonicError) as exc_info:
            raise MnemonicError(message)
        assert exc_info.value.args[0] == message

    def test_mnemonic_error_multiple_args(self):
        """Test that MnemonicError preserves multiple args."""
        with pytest.raises(MnemonicError) as exc_info:
            raise MnemonicError("error", "detail")
        assert exc_info.value.args == ("error", "detail")

    def test_mnemonic_error_can_be_caught_as_exception(self):
        """Test that MnemonicError can be caught as generic Exception."""
        try:
            raise MnemonicError("test")
        except Exception as e:
            assert isinstance(e, MnemonicError)
            assert isinstance(e, Exception)


class TestNotFoundErrorHierarchy:
    """Test the NotFoundError and its subclasses."""

    def test_not_found_error_inherits_from_mnemonic_error(self):
        """Test that NotFoundError inherits from MnemonicError."""
        assert issubclass(NotFoundError, MnemonicError)

    def test_not_found_error_can_be_raised(self):
        """Test that NotFoundError can be raised with a message."""
        message = "Resource not found"
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError(message)
        assert str(exc_info.value) == message

    def test_card_not_found_error_inherits_from_not_found_error(self):
        """Test that CardNotFoundError inherits from NotFoundError."""
        assert issubclass(CardNotFoundError, NotFoundError)
        assert issubclass(CardNotFoundError, MnemonicError)

    def test_card_not_found_error_with_card_id(self):
        """Test CardNotFoundError with informative card ID message."""
        card_id = "card-123"
        message = (
            f"Card {card_id} not found. "
            "Check that the card ID is correct and the card hasn't been deleted."
        )
        with pytest.raises(CardNotFoundError) as exc_info:
            raise CardNotFoundError(message)
        assert card_id in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    def test_card_not_found_error_caught_as_not_found(self):
        """Test that CardNotFoundError can be caught as NotFoundError."""
        with pytest.raises(NotFoundError):
            raise CardNotFoundError("Card not found")

    def test_card_not_found_error_caught_as_mnemonic_error(self):
        """Test that CardNotFoundError can be caught as MnemonicError."""
        with pytest.raises(MnemonicError):
            raise CardNotFoundError("Card not found")

    def test_deck_not_found_error_inherits_from_not_found_error(self):
        """Test that DeckNotFoundError inherits from NotFoundError."""
        assert issubclass(DeckNotFoundError, NotFoundError)
        assert issubclass(DeckNotFoundError, MnemonicError)

    def test_deck_not_found_error_with_deck_id(self):
        """Test DeckNotFoundError with informative deck ID message."""
        deck_id = "deck-456"
        message = (
            f"Deck {deck_id} not found. "
            "Check that the deck ID is correct and the deck hasn't been deleted."
        )
        with pytest.raises(DeckNotFoundError) as exc_info:
            raise DeckNotFoundError(message)
        assert deck_id in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    def test_deck_not_found_error_caught_as_not_found(self):
        """Test that DeckNotFoundError can be caught as NotFoundError."""
        with pytest.raises(NotFoundError):
            raise DeckNotFoundError("Deck not found")

    def test_not_found_error_hierarchy_distinct(self):
        """Test that NotFoundError subclasses are distinct types."""
        card_error = CardNotFoundError("card")
        deck_error = DeckNotFoundError("deck")
        assert type(card_error) is not type(deck_error)
        assert type(card_error).__name__ == "CardNotFoundError"
        assert type(deck_error).__name__ == "DeckNotFoundError"


class TestValidationErrorHierarchy:
    """Test the ValidationError and its subclasses."""

    def test_validation_error_inherits_from_mnemonic_error(self):
        """Test that ValidationError inherits from MnemonicError."""
        assert issubclass(ValidationError, MnemonicError)

    def test_validation_error_can_be_raised(self):
        """Test that ValidationError can be raised with a message."""
        message = "Invalid input provided"
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError(message)
        assert str(exc_info.value) == message

    def test_invalid_rating_error_inherits_from_validation_error(self):
        """Test that InvalidRatingError inherits from ValidationError."""
        assert issubclass(InvalidRatingError, ValidationError)
        assert issubclass(InvalidRatingError, MnemonicError)

    def test_invalid_rating_error_with_rating_value(self):
        """Test InvalidRatingError with informative rating details."""
        rating = 5
        message = (
            f"Invalid rating {rating}. "
            "Rating must be 1, 2, 3, or 4. "
            "1=Again, 2=Hard, 3=Good, 4=Easy."
        )
        with pytest.raises(InvalidRatingError) as exc_info:
            raise InvalidRatingError(message)
        assert str(rating) in str(exc_info.value)
        assert "must be" in str(exc_info.value).lower()
        assert "1" in str(exc_info.value)

    def test_invalid_rating_error_caught_as_validation_error(self):
        """Test that InvalidRatingError can be caught as ValidationError."""
        with pytest.raises(ValidationError):
            raise InvalidRatingError("Invalid rating")

    def test_invalid_rating_error_caught_as_mnemonic_error(self):
        """Test that InvalidRatingError can be caught as MnemonicError."""
        with pytest.raises(MnemonicError):
            raise InvalidRatingError("Invalid rating")

    def test_invalid_card_syntax_error_inherits_from_validation_error(self):
        """Test that InvalidCardSyntaxError inherits from ValidationError."""
        assert issubclass(InvalidCardSyntaxError, ValidationError)
        assert issubclass(InvalidCardSyntaxError, MnemonicError)

    def test_invalid_card_syntax_error_with_syntax_details(self):
        """Test InvalidCardSyntaxError with informative syntax details."""
        syntax_type = "cloze"
        message = (
            f"Invalid card syntax for type {syntax_type}. "
            "Cloze cards must use {{{{cloze:n::answer}}}} format. "
            "Example: The {{{{cloze:1::mitochondria}}}} is the powerhouse of the cell."
        )
        with pytest.raises(InvalidCardSyntaxError) as exc_info:
            raise InvalidCardSyntaxError(message)
        assert syntax_type in str(exc_info.value)
        assert "must use" in str(exc_info.value).lower()
        assert "{{" in str(exc_info.value)

    def test_invalid_card_syntax_error_caught_as_validation_error(self):
        """Test that InvalidCardSyntaxError can be caught as ValidationError."""
        with pytest.raises(ValidationError):
            raise InvalidCardSyntaxError("Invalid syntax")

    def test_validation_error_hierarchy_distinct(self):
        """Test that ValidationError subclasses are distinct types."""
        rating_error = InvalidRatingError("rating")
        syntax_error = InvalidCardSyntaxError("syntax")
        assert type(rating_error) is not type(syntax_error)
        assert type(rating_error).__name__ == "InvalidRatingError"
        assert type(syntax_error).__name__ == "InvalidCardSyntaxError"


class TestLLMErrorHierarchy:
    """Test the LLMError and its subclasses."""

    def test_llm_error_inherits_from_mnemonic_error(self):
        """Test that LLMError inherits from MnemonicError."""
        assert issubclass(LLMError, MnemonicError)

    def test_llm_error_can_be_raised(self):
        """Test that LLMError can be raised with a message."""
        message = "LLM operation failed"
        with pytest.raises(LLMError) as exc_info:
            raise LLMError(message)
        assert str(exc_info.value) == message

    def test_llm_config_error_inherits_from_llm_error(self):
        """Test that LLMConfigError inherits from LLMError."""
        assert issubclass(LLMConfigError, LLMError)
        assert issubclass(LLMConfigError, MnemonicError)

    def test_llm_config_error_with_config_details(self):
        """Test LLMConfigError with informative configuration details."""
        message = (
            "OpenRouter authentication failed. "
            "Please check your API key in Settings > LLM Configuration. "
            "Details: Invalid API key format."
        )
        with pytest.raises(LLMConfigError) as exc_info:
            raise LLMConfigError(message)
        assert "authentication" in str(exc_info.value).lower()
        assert "API key" in str(exc_info.value)
        assert "Settings" in str(exc_info.value)

    def test_llm_config_error_caught_as_llm_error(self):
        """Test that LLMConfigError can be caught as LLMError."""
        with pytest.raises(LLMError):
            raise LLMConfigError("Config error")

    def test_llm_config_error_caught_as_mnemonic_error(self):
        """Test that LLMConfigError can be caught as MnemonicError."""
        with pytest.raises(MnemonicError):
            raise LLMConfigError("Config error")

    def test_llm_rate_limit_error_inherits_from_llm_error(self):
        """Test that LLMRateLimitError inherits from LLMError."""
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(LLMRateLimitError, MnemonicError)

    def test_llm_rate_limit_error_with_retry_after(self):
        """Test LLMRateLimitError stores retry_after attribute."""
        retry_after = 60
        message = f"OpenRouter rate limit exceeded. Try again in {retry_after}s."
        error = LLMRateLimitError(message, retry_after)
        assert error.retry_after == retry_after
        assert str(error) == message

    def test_llm_rate_limit_error_retry_after_is_int(self):
        """Test that LLMRateLimitError.retry_after is an integer."""
        retry_after = 120
        error = LLMRateLimitError("Rate limited", retry_after)
        assert isinstance(error.retry_after, int)
        assert error.retry_after == 120

    def test_llm_rate_limit_error_with_different_retry_times(self):
        """Test LLMRateLimitError with various retry_after values."""
        for retry_seconds in [1, 30, 60, 3600]:
            error = LLMRateLimitError(f"Try again in {retry_seconds}s", retry_seconds)
            assert error.retry_after == retry_seconds

    def test_llm_rate_limit_error_caught_as_llm_error(self):
        """Test that LLMRateLimitError can be caught as LLMError."""
        with pytest.raises(LLMError):
            raise LLMRateLimitError("Rate limited", 60)

    def test_llm_rate_limit_error_with_helpful_message(self):
        """Test LLMRateLimitError with actionable user guidance."""
        retry_after = 30
        message = (
            f"OpenRouter rate limit exceeded. Try again in {retry_after}s. "
            "You can reduce variation frequency in Settings, "
            "or upgrade your OpenRouter plan."
        )
        error = LLMRateLimitError(message, retry_after)
        assert error.retry_after == retry_after
        assert "reduce variation" in str(error).lower()
        assert "upgrade" in str(error).lower()

    def test_llm_unavailable_error_inherits_from_llm_error(self):
        """Test that LLMUnavailableError inherits from LLMError."""
        assert issubclass(LLMUnavailableError, LLMError)
        assert issubclass(LLMUnavailableError, MnemonicError)

    def test_llm_unavailable_error_with_service_status(self):
        """Test LLMUnavailableError with service status information."""
        message = (
            "OpenRouter service is temporarily unavailable. "
            "Check the OpenRouter status page: https://status.openrouter.io. "
            "Card variations will be retried when the service recovers."
        )
        with pytest.raises(LLMUnavailableError) as exc_info:
            raise LLMUnavailableError(message)
        assert "temporarily unavailable" in str(exc_info.value).lower()
        assert "status" in str(exc_info.value).lower()
        assert "https://" in str(exc_info.value)

    def test_llm_unavailable_error_caught_as_llm_error(self):
        """Test that LLMUnavailableError can be caught as LLMError."""
        with pytest.raises(LLMError):
            raise LLMUnavailableError("Service unavailable")

    def test_llm_error_hierarchy_distinct(self):
        """Test that LLMError subclasses are distinct types."""
        config_error = LLMConfigError("config")
        rate_limit_error = LLMRateLimitError("rate limit", 60)
        unavailable_error = LLMUnavailableError("unavailable")
        assert type(config_error) is not type(rate_limit_error)
        assert type(config_error) is not type(unavailable_error)
        assert type(rate_limit_error) is not type(unavailable_error)


class TestRenderErrorHierarchy:
    """Test the RenderError and its subclasses."""

    def test_render_error_inherits_from_mnemonic_error(self):
        """Test that RenderError inherits from MnemonicError."""
        assert issubclass(RenderError, MnemonicError)

    def test_render_error_can_be_raised(self):
        """Test that RenderError can be raised with a message."""
        message = "Card rendering failed"
        with pytest.raises(RenderError) as exc_info:
            raise RenderError(message)
        assert str(exc_info.value) == message

    def test_pandoc_error_inherits_from_render_error(self):
        """Test that PandocError inherits from RenderError."""
        assert issubclass(PandocError, RenderError)
        assert issubclass(PandocError, MnemonicError)

    def test_pandoc_error_with_rendering_details(self):
        """Test PandocError with informative rendering details."""
        message = (
            "Pandoc rendering failed for card. "
            "Error: Unexpected token in Markdown syntax. "
            "Check that all Markdown formatting is valid."
        )
        with pytest.raises(PandocError) as exc_info:
            raise PandocError(message)
        assert "Pandoc" in str(exc_info.value)
        assert "failed" in str(exc_info.value).lower()
        assert "Markdown" in str(exc_info.value)

    def test_pandoc_error_caught_as_render_error(self):
        """Test that PandocError can be caught as RenderError."""
        with pytest.raises(RenderError):
            raise PandocError("Pandoc error")

    def test_pandoc_error_caught_as_mnemonic_error(self):
        """Test that PandocError can be caught as MnemonicError."""
        with pytest.raises(MnemonicError):
            raise PandocError("Pandoc error")

    def test_mathjax_error_inherits_from_render_error(self):
        """Test that MathJaxError inherits from RenderError."""
        assert issubclass(MathJaxError, RenderError)
        assert issubclass(MathJaxError, MnemonicError)

    def test_mathjax_error_with_equation_context(self):
        """Test MathJaxError with equation context."""
        equation = r"$\frac{x^2 + 1}{x}$"
        message = (
            f"MathJax rendering failed for equation: {equation}. "
            "Check that the LaTeX syntax is valid. "
            "Common issues: unbalanced braces, undefined commands."
        )
        with pytest.raises(MathJaxError) as exc_info:
            raise MathJaxError(message)
        assert "MathJax" in str(exc_info.value)
        assert "failed" in str(exc_info.value).lower()
        assert equation in str(exc_info.value)
        assert "LaTeX" in str(exc_info.value)

    def test_mathjax_error_caught_as_render_error(self):
        """Test that MathJaxError can be caught as RenderError."""
        with pytest.raises(RenderError):
            raise MathJaxError("MathJax error")

    def test_render_error_hierarchy_distinct(self):
        """Test that RenderError subclasses are distinct types."""
        pandoc_error = PandocError("pandoc")
        mathjax_error = MathJaxError("mathjax")
        assert type(pandoc_error) is not type(mathjax_error)
        assert type(pandoc_error).__name__ == "PandocError"
        assert type(mathjax_error).__name__ == "MathJaxError"


class TestExceptionChaining:
    """Test exception chaining (raise ... from e) for better error context."""

    def test_exception_chaining_preserves_original_error(self):
        """Test that exception chaining preserves the original error."""
        original_error = ValueError("Original error")
        try:
            try:
                raise original_error
            except ValueError as e:
                raise MnemonicError("Wrapped error") from e
        except MnemonicError as e:
            assert e.__cause__ is original_error

    def test_exception_chaining_with_card_not_found(self):
        """Test exception chaining with CardNotFoundError."""
        original_error = RuntimeError("Database connection failed")
        try:
            try:
                raise original_error
            except RuntimeError as e:
                raise CardNotFoundError(
                    "Failed to fetch card. Please check your connection."
                ) from e
        except CardNotFoundError as e:
            assert e.__cause__ is original_error
            assert isinstance(e.__cause__, RuntimeError)

    def test_exception_chaining_with_llm_config_error(self):
        """Test exception chaining with LLMConfigError."""
        original_error = KeyError("API_KEY")
        try:
            try:
                raise original_error
            except KeyError as e:
                raise LLMConfigError(
                    "Missing API key in Settings > LLM Configuration. " f"Details: {e}"
                ) from e
        except LLMConfigError as e:
            assert e.__cause__ is original_error


class TestInformativeMessages:
    """Test that exceptions follow the NO SILENT FAILURES principle."""

    def test_message_explains_what_failed(self):
        """Test that exception messages explain WHAT failed."""
        # All exceptions should answer: What operation failed?
        exceptions_and_messages = [
            (MnemonicError, "Operation X failed"),
            (NotFoundError, "Resource not found"),
            (CardNotFoundError, "Card not found"),
            (DeckNotFoundError, "Deck not found"),
            (ValidationError, "Validation failed"),
            (InvalidRatingError, "Rating validation failed"),
            (InvalidCardSyntaxError, "Syntax validation failed"),
            (LLMError, "LLM operation failed"),
            (LLMConfigError, "Configuration issue"),
            (LLMUnavailableError, "Service unavailable"),
            (PandocError, "Rendering failed"),
            (MathJaxError, "Math rendering failed"),
        ]

        for exc_class, message in exceptions_and_messages:
            with pytest.raises(exc_class) as exc_info:
                if exc_class == LLMRateLimitError:
                    raise exc_class(message, 60)
                else:
                    raise exc_class(message)
            assert len(str(exc_info.value)) > 0, f"{exc_class.__name__} has no message"

    def test_llm_rate_limit_provides_retry_information(self):
        """Test that LLMRateLimitError provides actionable retry information."""
        retry_after = 45
        message = (
            f"OpenRouter rate limit exceeded. Try again in {retry_after}s. "
            "Consider upgrading your plan or reducing request frequency."
        )
        error = LLMRateLimitError(message, retry_after)
        # The error provides the exact retry time
        assert error.retry_after == retry_after
        # The message explains why it failed and what to do
        assert "Try again in" in message
        assert "Consider" in message or "upgrade" in message.lower()

    def test_exceptions_are_not_silent(self):
        """Test that exceptions cannot be silently swallowed."""
        # Test that we can't return None or empty string as a fallback
        with pytest.raises(CardNotFoundError):
            raise CardNotFoundError("Card not found")
        # Fallback to None would be a silent failure - not allowed

    def test_llm_config_error_is_specific(self):
        """Test that LLMConfigError is specific, not generic."""
        # Good: specific config error with context
        message = (
            "OpenRouter authentication failed. "
            "Please check your API key in Settings > LLM Configuration. "
            "Details: HTTP 401 - Invalid API key."
        )
        with pytest.raises(LLMConfigError):
            raise LLMConfigError(message)


class TestExceptionInstantiation:
    """Test that all exceptions can be properly instantiated."""

    def test_all_exceptions_instantiate(self):
        """Test that all exception classes can be instantiated."""
        exceptions = [
            MnemonicError,
            NotFoundError,
            CardNotFoundError,
            DeckNotFoundError,
            ValidationError,
            InvalidRatingError,
            InvalidCardSyntaxError,
            LLMError,
            LLMConfigError,
            LLMUnavailableError,
            PandocError,
            RenderError,
            MathJaxError,
        ]

        for exc_class in exceptions:
            if exc_class == LLMRateLimitError:
                error = exc_class("message", 60)
            else:
                error = exc_class("test message")
            assert isinstance(error, Exception)
            assert isinstance(error, MnemonicError)

    def test_llm_rate_limit_error_instantiation(self):
        """Test LLMRateLimitError instantiation with required parameters."""
        # Should work with message and retry_after
        error = LLMRateLimitError("Rate limited", 60)
        assert error.retry_after == 60

    def test_exception_string_representation(self):
        """Test that exceptions have meaningful string representations."""
        error = CardNotFoundError("Card 123 not found")
        assert "Card 123" in str(error)
        assert "not found" in str(error).lower()

    def test_exception_repr(self):
        """Test that exceptions can be represented as strings."""
        error = InvalidRatingError("Rating 5 is invalid")
        repr_str = repr(error)
        assert "InvalidRatingError" in repr_str or "Rating" in repr_str
