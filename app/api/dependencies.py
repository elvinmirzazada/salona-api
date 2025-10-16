from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Customers
from app.services.auth import get_current_id, verify_token
from app.services.crud import user as crud_user, customer as crud_customer
from app.models.models import Users, Customers

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Users:
    """Get the current authenticated user from JWT token."""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Extract user ID from token
        user_id = get_current_id(credentials.credentials)
        if user_id is None:
            raise credentials_exception
            
    except Exception:
        raise credentials_exception
    
    # Get user from database
    user = crud_user.get(db, id=user_id)
    if user is None:
        raise credentials_exception
        
    return user


def get_current_customer(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> Customers:
    """Get the current authenticated customer from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Extract user ID from token
        customer_id = get_current_id(credentials.credentials)
        if customer_id is None:
            raise credentials_exception

    except Exception:
        raise credentials_exception

    # Get user from database
    customer = crud_customer.get(db, id=customer_id)

    if customer is None:
        raise credentials_exception

    return customer


def get_token_payload(
        credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Extract and return the payload from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Extract user ID from token
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception

    except Exception:
        raise credentials_exception

    return payload



async def get_current_active_user(
    current_user: Users = Depends(get_current_user)
) -> Users:
    """Get the current active user (can be extended for status checks)."""
    # Here you can add additional checks like account status, subscription, etc.
    return current_user


async def get_current_active_customer(
    current_customer: Customers = Depends(get_current_customer)
) -> Customers:
    """Get the current active customer (can be extended for status checks)."""
    # Here you can add additional checks like account status, subscription, etc.
    return current_customer


def get_current_company_id(token_payload: dict = Depends(get_token_payload)) -> str:
    company_id = token_payload.get("company_id")
    return company_id