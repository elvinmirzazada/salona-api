from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings
import datetime as dt_obj

# Configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 60 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 1 week

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(dt_obj.UTC) + expires_delta
    else:
        expire = datetime.now(dt_obj.UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(dt_obj.UTC) + expires_delta
    else:
        expire = datetime.now(dt_obj.UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_token_pair(id: str, email: str, actor: str, ver: str = '1', company_id: Optional[str] = None) -> Dict:
    """Create both access and refresh tokens."""
    data = {"sub": str(id), "email": email, "actor": actor, "ver": ver, 'company_id': company_id}
    access_token = create_access_token(data)
    refresh_token = create_refresh_token(data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "at_expires_in": int(ACCESS_TOKEN_EXPIRE_MINUTES * 60), # seconds
        "rt_expires_in": int(REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)  # seconds
    }


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check expiration
        exp = payload.get("exp")
        if exp is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing expiration",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if datetime.fromtimestamp(exp, dt_obj.UTC) < datetime.now(dt_obj.UTC):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token has expired. Please refresh your token or login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except ExpiredSignatureError:
        # Handle expired token specifically
        print("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as ex:
        # Handle all other JWT errors (invalid signature, malformed token, etc.)
        print(f"Token verification error: {ex}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_id(token: str):
    """Extract user ID from access token."""
    payload = verify_token(token, "access")
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None
        
    try:
        return user_id
    except (ValueError, TypeError):
        return None


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """Create a new access token using a refresh token."""
    payload = verify_token(refresh_token, "refresh")
    if payload is None:
        return None
        
    id = payload.get("sub")
    email = payload.get("email")
    actor = payload.get("actor")
    ver = payload.get("ver")

    if not id or not email:
        return None
        
    try:
        data = {"sub": id, "email": email, "actor": actor, "ver": ver}
        access_token = create_access_token(data)
        return {
            "access_token": access_token,
            'refresh_token': refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
        }
    except (ValueError, TypeError):
        return None
