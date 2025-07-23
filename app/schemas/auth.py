from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    identifier: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    professional_id: Optional[int] = None
    identifier: Optional[str] = None
