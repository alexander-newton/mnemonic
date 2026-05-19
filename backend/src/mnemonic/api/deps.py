"""Dependency injection for FastAPI application.

Provides common dependencies used across API endpoints such as database sessions
and current user authentication.
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from mnemonic.config import settings
from mnemonic.db.models.user import User
from mnemonic.db.repositories.user import UserRepository
from mnemonic.services.auth import AuthService

# HTTP Bearer scheme for JWT tokens
http_bearer = HTTPBearer()


def get_db() -> Session:
    """Get a database session.

    This is a placeholder that should be overridden with actual database
    session management in the actual app implementation.

    Yields:
        SQLAlchemy Session for database operations.
    """
    # This will be implemented with actual database initialization
    # For now, it's a placeholder for dependency injection
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: object = Depends(http_bearer),
    session: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token.

    Validates the JWT token from Authorization header and returns the
    corresponding user from the database.

    Args:
        credentials: HTTP Bearer credentials from Authorization header.
        session: Database session for user lookup.

    Returns:
        User object for the authenticated user.

    Raises:
        HTTPException: If token is invalid, expired, or user not found (401).
    """
    # Extract token from credentials object
    if not hasattr(credentials, "credentials"):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = credentials.credentials
    auth_service = AuthService(UserRepository())

    # Verify token and get user_id
    user_id = auth_service.verify_access_token(token)

    # Fetch user from database
    user_repo = UserRepository()
    try:
        user = user_repo.get(session, user_id)
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="User not found") from e
