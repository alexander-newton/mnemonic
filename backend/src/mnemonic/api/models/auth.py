"""Pydantic models for authentication API.

Defines request and response schemas for user registration and login endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request body for user registration endpoint.

    Attributes:
        email: Valid email address (unique constraint enforced in DB).
        password: Password (minimum 8 characters).
    """

    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """Request body for user login endpoint.

    Attributes:
        email: User's email address.
        password: User's password.
    """

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User object returned in API responses.

    Never includes password_hash.

    Attributes:
        id: User's unique identifier.
        email: User's email address.
        created_at: Timestamp when user was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime


class LoginResponse(BaseModel):
    """Response body for login endpoint.

    Attributes:
        token: JWT access token for subsequent authenticated requests.
        user: User object (without sensitive data).
    """

    token: str
    user: UserResponse
