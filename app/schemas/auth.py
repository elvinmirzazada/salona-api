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
    rt_expires_in: int
    at_expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    company_id: Optional[str] = None


class GoogleAuthorizationRequest(BaseModel):
    """Request to initiate Google OAuth flow."""
    pass


class GoogleAuthorizationResponse(BaseModel):
    """Response with Google authorization URL."""
    authorization_url: str
    state: str


class GoogleCallbackRequest(BaseModel):
    """Request with authorization code and state from Google callback."""
    code: str
    state: str
    redirect_uri: Optional[str] = None


class GoogleOAuthResponse(BaseModel):
    """Response after successful Google OAuth."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user_email: str
    user_name: Optional[str] = None
