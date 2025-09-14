from typing import List
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import Customer, CustomerCreate, ClientUpdate
from app.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest, VerificationRequest
from app.services.crud import customer as crud_customer
from app.schemas.schemas import ResponseMessage
from app.services.auth import hash_password, verify_password, create_token_pair, refresh_access_token


router = APIRouter()


@router.post("/auth/signup", response_model=Customer, status_code=status.HTTP_201_CREATED)
def create_customer(
    *,
    db: Session = Depends(get_db),
    customer_in: CustomerCreate
) -> Customer:
    """
    Create a new customer.
    """

    # Check if customer with this email already exists
    existing_customer = crud_customer.get_by_email(
        db=db,
        email=customer_in.email,
        business_id=customer_in.business_id
    )
    
    if existing_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer with this email already exists for this business"
        )

    customer_in.password = hash_password(customer_in.password)

    customer = crud_customer.create(db=db, obj_in=customer_in)
    return customer


@router.post("/auth/verify_email", response_model=ResponseMessage)
def get_customer(
    *,
    db: Session = Depends(get_db),
    verification_in: VerificationRequest
) -> ResponseMessage:
    """
    Verify email.
    """
    token = crud_customer.get_verification_token(db=db, token=verification_in.token, type="email")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    if token.status != "pending" or token.expires_at < func.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    result = crud_customer.verify_token(db=db, db_obj=token)
    if result:
        return ResponseMessage(message="Email verified successfully")
    
    return ResponseMessage(message="Email verification failed")

@router.post("/auth/login", response_model=TokenResponse)
async def customer_login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Login customer using email and return JWT tokens.
    """
    customer = crud_customer.get_by_email(db, email=login_data.email)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if customer.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account is not active"
        )

    # Verify password
    if not verify_password(login_data.password, customer.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Create token pair
    tokens = create_token_pair(customer.id, customer.email, actor="customer", ver="1")
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,  # only over HTTPS
        samesite="strict"
    )
    return TokenResponse(**tokens)


@router.post("/auth/refresh-token", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    response: Response,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    """
    tokens = refresh_access_token(refresh_data.refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,  # only over HTTPS
        samesite="strict"
    )
    return TokenResponse(**tokens)

@router.put("/auth/logout", response_model=ResponseMessage)
def logout_customer(
    response: Response
) -> ResponseMessage:
    """
    Logout customer by clearing the refresh token cookie.
    """
    response.delete_cookie(key="refresh_token")
    return ResponseMessage(message="Logged out successfully")

# TODO: Add endpoints for password reset, forgot password, etc.
