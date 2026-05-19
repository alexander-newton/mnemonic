"""Authentication service for user registration and login.

Handles password hashing, JWT token creation/verification, and user authentication.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from mnemonic.config import settings
from mnemonic.db.models.user import User
from mnemonic.db.repositories.user import UserRepository
from mnemonic.exceptions import ValidationError

# Password hashing context using pbkdf2_sha256 (pure Python, no external deps)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class AuthService:
    """Service for handling user authentication operations.

    Provides methods for:
    - Password hashing and verification (bcrypt)
    - JWT token creation and validation
    - User registration with validation
    - User authentication with email/password
    """

    def __init__(self, user_repo: UserRepository) -> None:
        """Initialize AuthService with a UserRepository.

        Args:
            user_repo: Repository for user data access.
        """
        self.user_repo = user_repo

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password using bcrypt.

        Args:
            password: Plaintext password to hash.

        Returns:
            Hashed password (bcrypt format).
        """
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verify plaintext password against bcrypt hash.

        Args:
            plain: Plaintext password to verify.
            hashed: Bcrypt hash to verify against.

        Returns:
            True if password matches hash, False otherwise.
        """
        return pwd_context.verify(plain, hashed)

    def create_access_token(self, user_id: uuid.UUID, expires_delta: int | None = None) -> str:
        """Create a JWT access token for a user.

        Args:
            user_id: User's UUID to encode in token.
            expires_delta: Token expiration time in minutes (relative to now).
                          If None, uses default from settings.

        Returns:
            JWT access token string.
        """
        if expires_delta is None:
            expires_delta = settings.jwt_expiration_minutes

        expire = datetime.now(timezone.utc) + timedelta(minutes=expires_delta)

        to_encode = {
            "sub": str(user_id),
            "exp": expire,
        }

        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
        return encoded_jwt

    def verify_access_token(self, token: str) -> uuid.UUID:
        """Verify JWT access token and extract user ID.

        Args:
            token: JWT token to verify.

        Returns:
            User ID extracted from token.

        Raises:
            HTTPException: If token is invalid or expired (401 status).
        """
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid authentication credentials")
            return uuid.UUID(user_id)
        except JWTError as e:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials") from e

    def _validate_email(self, email: str) -> None:
        """Validate email format.

        Args:
            email: Email address to validate.

        Raises:
            ValidationError: If email format is invalid.
        """
        # Basic email validation - pydantic EmailStr will validate more thoroughly
        # This is a secondary check
        if not email or "@" not in email:
            raise ValidationError("Please provide a valid email address")

    def _validate_password(self, password: str) -> None:
        """Validate password strength.

        Args:
            password: Password to validate.

        Raises:
            ValidationError: If password does not meet requirements.
        """
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")

    def register_user(self, session: Session, email: str, password: str) -> User:
        """Register a new user with email and password.

        Validates email format and password strength before creation.
        Hashes password using bcrypt.

        Args:
            session: SQLAlchemy session for database access.
            email: User's email address (must be unique).
            password: User's plaintext password.

        Returns:
            Created User object (without password hash exposed).

        Raises:
            ValidationError: If email is invalid or password too weak.
            ValueError: If email already exists.
        """
        # Validate inputs
        self._validate_email(email)
        self._validate_password(password)

        # Check if email already exists
        if self.user_repo.exists_by_email(session, email):
            raise ValueError(f"User with email '{email}' already exists")

        # Hash password and create user
        password_hash = self.hash_password(password)
        user = self.user_repo.create_user(
            session,
            email=email,
            password_hash=password_hash,
        )

        return user

    def authenticate_user(self, session: Session, email: str, password: str) -> User:
        """Authenticate user with email and password.

        Args:
            session: SQLAlchemy session for database access.
            email: User's email address.
            password: User's plaintext password.

        Returns:
            User object if authentication successful.

        Raises:
            ValidationError: If credentials are invalid (with generic message).
        """
        try:
            user = self.user_repo.get_by_email(session, email)
        except Exception as e:
            # Intentionally generic - don't reveal if email exists
            raise ValidationError("Invalid credentials") from e

        if not self.verify_password(password, user.password_hash):
            raise ValidationError("Invalid credentials")

        return user
