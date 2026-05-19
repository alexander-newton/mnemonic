"""Test script to verify environment setup."""

import sys


def test_python_version() -> None:
    """Verify Python version meets minimum requirement."""
    assert sys.version_info >= (3, 11), "Python 3.11+ required"


def test_fastapi_import() -> None:
    """Verify FastAPI is installed and importable."""
    import fastapi  # noqa: F401

    assert hasattr(fastapi, "FastAPI")


def test_sqlalchemy_import() -> None:
    """Verify SQLAlchemy is installed and importable."""
    import sqlalchemy  # noqa: F401

    assert hasattr(sqlalchemy, "create_engine")


def test_pydantic_import() -> None:
    """Verify Pydantic is installed and importable."""
    import pydantic  # noqa: F401

    assert hasattr(pydantic, "BaseModel")


def test_redis_import() -> None:
    """Verify Redis is installed and importable."""
    import redis  # noqa: F401

    assert hasattr(redis, "Redis")


def test_jose_import() -> None:
    """Verify Python-Jose is installed and importable."""
    from jose import jwt  # noqa: F401

    assert jwt is not None


def test_passlib_import() -> None:
    """Verify Passlib is installed and importable."""
    from passlib.context import CryptContext  # noqa: F401

    assert CryptContext is not None


def test_httpx_import() -> None:
    """Verify HTTPx is installed and importable."""
    import httpx  # noqa: F401

    assert hasattr(httpx, "Client")


def test_dspy_import() -> None:
    """Verify DSPy is installed and importable."""
    import dspy  # noqa: F401

    assert hasattr(dspy, "ChainOfThought")


def test_pypandoc_import() -> None:
    """Verify Pypandoc is installed and importable."""
    import pypandoc  # noqa: F401

    assert hasattr(pypandoc, "convert_text")


def test_yaml_import() -> None:
    """Verify PyYAML is installed and importable."""
    import yaml  # noqa: F401

    assert hasattr(yaml, "safe_load")


def test_dotenv_import() -> None:
    """Verify Python-dotenv is installed and importable."""
    import dotenv  # noqa: F401

    assert hasattr(dotenv, "load_dotenv")


def test_pytest_import() -> None:
    """Verify Pytest is installed and importable."""
    import pytest as pytest_module  # noqa: F401

    assert hasattr(pytest_module, "main")


def test_app_import() -> None:
    """Verify the main FastAPI app can be imported."""
    from mnemonic.main import app  # noqa: F401, type: ignore[import-untyped]

    assert app is not None
