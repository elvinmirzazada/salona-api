from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from pydantic import UUID4
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.responses import DataResponse
from app.schemas.schemas import ResponseMessage
from app.schemas.schemas import UserCreate,AvailabilityResponse
from app.services.auth import hash_password, verify_password, create_token_pair
from app.services.crud import user as crud_user
from app.services.crud import booking as crud_booking
from app.models.enums import AvailabilityType
from app.services.crud import user_availability as crud_availability


router = APIRouter()

@router.post("/auth/signup", response_model=ResponseMessage, status_code=status.HTTP_201_CREATED)
async def create_user(
    *,
    db: Session = Depends(get_db),
    response: Response,
    user_in: UserCreate
) -> ResponseMessage:
    """
    Register a new user.
    """

    try:
        existing_customer = crud_user.get_by_email(
            db=db,
            email=user_in.email
        )
        if existing_customer:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return ResponseMessage(message="User with this email already exists for this business", status="error")

        user_in.password = hash_password(user_in.password)
        crud_user.create(db=db, obj_in=user_in)
        response.status_code = status.HTTP_201_CREATED
        return ResponseMessage(message="User created successfully", status="success")
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ResponseMessage(message=f"Internal server error: {str(e)}", status="error")


@router.post("/auth/login", response_model=TokenResponse)
async def user_login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Login professional using mobile number or email and return JWT tokens.
    """
    # Try to get professional by mobile number first
    user = crud_user.get_by_email(db, email=login_data.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Verify password
    if not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Create token pair
    tokens = create_token_pair(user.id, user.email, actor="user", ver="1")
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,  # only over HTTPS
        samesite="strict"
    )
    return TokenResponse(**tokens)


@router.put("/auth/logout")
async def logout_user(response: Response):
    """
    Logout professional by clearing the refresh token cookie
    """
    try:
        response.delete_cookie(key="refresh_token")
        return ResponseMessage(message="Logged out successfully", status="success")
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ResponseMessage(message=f"Internal server error: {str(e)}", status="error")
