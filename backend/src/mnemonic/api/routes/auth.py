"""Authentication API endpoints for user registration and login.

Provides endpoints for:
- POST /auth/register - Register new user
- POST /auth/login - Authenticate user and get JWT token
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from mnemonic.api.deps import get_db
from mnemonic.api.models.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
)
from mnemonic.db.repositories.user import UserRepository
from mnemonic.exceptions import ValidationError
from mnemonic.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(_session: Session = Depends(get_db)) -> AuthService:
    """Get AuthService instance with injected dependencies.

    Args:
        _session: Database session (unused, but required for dependency injection).

    Returns:
        AuthService instance.
    """
    user_repo = UserRepository()
    return AuthService(user_repo)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: RegisterRequest,
    session: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Register a new user account.

    Validates email format and password strength, creates user with hashed password.

    Args:
        data: Registration request containing email and password.
        session: Database session.
        auth_service: Authentication service instance.

    Returns:
        UserResponse: Created user object (without password hash).

    Raises:
        400: If email already exists or validation fails.
        422: If request data is invalid (bad format).
    """
    try:
        user = auth_service.register_user(session, data.email, data.password)
        return UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    session: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Authenticate user and return JWT access token.

    Validates email and password against stored user record.
    Returns JWT token for use in subsequent authenticated requests.

    Args:
        data: Login request containing email and password.
        session: Database session.
        auth_service: Authentication service instance.

    Returns:
        LoginResponse: JWT token and user object.

    Raises:
        401: If credentials are invalid (user not found or password wrong).
        422: If request data is invalid (bad format).
    """
    try:
        user = auth_service.authenticate_user(session, data.email, data.password)
        token = auth_service.create_access_token(user.id)

        return LoginResponse(
            token=token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                created_at=user.created_at,
            ),
        )
    except ValidationError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
