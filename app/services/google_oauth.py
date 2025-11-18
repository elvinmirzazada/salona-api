"""Google OAuth service for authentication and token exchange."""

import secrets
import string
from typing import Optional, Dict, Any
import requests
from app.core.config import settings


class GoogleOAuthService:
    """Service to handle Google OAuth flow."""
    
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    @staticmethod
    def get_authorization_url(state: str, redirect_uri: Optional[str] = None) -> str:
        """
        Generate the Google authorization URL for user consent.
        
        Args:
            state: State token for CSRF protection
            redirect_uri: Optional override for redirect URI
            
        Returns:
            Authorization URL to redirect user to
        """
        redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI
        
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent"
        }
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GoogleOAuthService.GOOGLE_AUTH_URL}?{query_string}"
    
    @staticmethod
    def exchange_code_for_token(code: str, redirect_uri: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from Google
            redirect_uri: Optional override for redirect URI
            
        Returns:
            Dictionary with token info or None if exchange fails
        """
        redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI
        
        payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        try:
            response = requests.post(GoogleOAuthService.GOOGLE_TOKEN_URL, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error exchanging code for token: {str(e)}")
            return None
    
    @staticmethod
    def get_user_info(access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from Google using access token.
        
        Args:
            access_token: Google access token
            
        Returns:
            Dictionary with user info (email, name, picture, etc.) or None if request fails
        """
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            response = requests.get(GoogleOAuthService.GOOGLE_USERINFO_URL, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting user info: {str(e)}")
            return None
    
    @staticmethod
    def generate_random_password(length: int = 16) -> str:
        """
        Generate a random password for users created via OAuth.
        
        Args:
            length: Password length
            
        Returns:
            Random password string
        """
        characters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    @staticmethod
    def generate_state_token() -> str:
        """
        Generate a state token for CSRF protection.
        
        Returns:
            Random state token
        """
        return secrets.token_urlsafe(32)

