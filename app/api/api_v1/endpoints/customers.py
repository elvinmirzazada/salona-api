from typing import List
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import Customer, CustomerCreate
from app.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest, VerificationRequest
from app.services.crud import customer as crud_customer
from app.schemas.schemas import ResponseMessage
from app.services.auth import hash_password, verify_password, create_token_pair, refresh_access_token


router = APIRouter()


@router.post("/auth/signup", response_model=ResponseMessage, status_code=status.HTTP_201_CREATED)
def create_customer(
    *,
    db: Session = Depends(get_db),
    customer_in: CustomerCreate,
    response: Response
) -> ResponseMessage:
    """
    Create a new customer.
    """
    try:
        existing_customer = crud_customer.get_by_email(
            db=db,
            email=customer_in.email
        )
        if existing_customer:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return ResponseMessage(message="Customer with this email already exists for this business", status="error")
        customer_in.password = hash_password(customer_in.password)
        crud_customer.create(db=db, obj_in=customer_in)
        response.status_code = status.HTTP_201_CREATED
        return ResponseMessage(message="Customer created successfully", status="success")
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ResponseMessage(message=f"Internal server error: {str(e)}", status="error")


@router.post("/auth/verify_email", response_model=ResponseMessage)
def get_customer(
    *,
    db: Session = Depends(get_db),
    verification_in: VerificationRequest,
    response: Response
) -> ResponseMessage:
    """
    Verify email.
    """
    try:
        token = crud_customer.get_verification_token(db=db, token=verification_in.token, type="email")
        if not token:
            response.status_code = status.HTTP_404_NOT_FOUND
            return ResponseMessage(message="Token not found", status="error")
        if token.status != "pending" or token.expires_at < func.now():
            response.status_code = status.HTTP_400_BAD_REQUEST
            return ResponseMessage(message="Invalid or expired token", status="error")
        result = crud_customer.verify_token(db=db, db_obj=token)
        if result:
            return ResponseMessage(message="Email verified successfully", status="success")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return ResponseMessage(message="Email verification failed", status="error")
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ResponseMessage(message=f"Internal server error: {str(e)}", status="error")

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


@router.post("/auth/refresh-token", response_model=ResponseMessage)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    response: Response,
    db: Session = Depends(get_db)
) -> ResponseMessage:
    """
    Refresh access token using refresh token.
    """
    try:
        tokens = refresh_access_token(refresh_data.refresh_token)
        if not tokens:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return ResponseMessage(message="Invalid refresh token", status="error")
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=True,  # only over HTTPS
            samesite="strict"
        )
        return ResponseMessage(message="Token refreshed successfully", status="success")
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ResponseMessage(message=f"Internal server error: {str(e)}", status="error")

@router.put("/auth/logout", response_model=ResponseMessage)
def logout_customer(
    response: Response
) -> ResponseMessage:
    """
    Logout customer by clearing the refresh token cookie.
    """
    try:
        response.delete_cookie(key="refresh_token")
        return ResponseMessage(message="Logged out successfully", status="success")
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ResponseMessage(message=f"Internal server error: {str(e)}", status="error")

# TODO: Add endpoints for password reset, forgot password, etc.
