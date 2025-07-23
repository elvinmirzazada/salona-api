from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.auth import get_current_professional_id
from app.services.crud import professional as crud_professional
from app.models.models import Professional

security = HTTPBearer()


async def get_current_professional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Professional:
    """Get the current authenticated professional from JWT token."""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Extract professional ID from token
        professional_id = get_current_professional_id(credentials.credentials)
        if professional_id is None:
            raise credentials_exception
            
    except Exception:
        raise credentials_exception
    
    # Get professional from database
    professional = crud_professional.get(db, id=professional_id)
    if professional is None:
        raise credentials_exception
        
    return professional


async def get_current_active_professional(
    current_professional: Professional = Depends(get_current_professional)
) -> Professional:
    """Get the current active professional (can be extended for status checks)."""
    # Here you can add additional checks like account status, subscription, etc.
    return current_professional
