from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    email: str
    password: str
    company_id: Optional[str] = None  # UUID as string, optional during login


class VerificationRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    company_id: Optional[str] = None
