"""Tests for optimization exception hierarchy."""

from mnemonic.exceptions import (
    InsufficientDataError,
    MnemonicError,
    OptimizationError,
)


def test_optimization_errors_inherit_from_mnemonic_error():
    assert issubclass(OptimizationError, MnemonicError)
    assert issubclass(InsufficientDataError, OptimizationError)


def test_insufficient_data_error_message_names_shortfall():
    err = InsufficientDataError("rephrase", have=3, need=20)
    msg = str(err)
    assert "rephrase" in msg
    assert "3" in msg
    assert "20" in msg
