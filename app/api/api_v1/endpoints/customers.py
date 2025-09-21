from typing import List
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import Customer, CustomerCreate
from app.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest, VerificationRequest
from app.services.crud import customer as crud_customer
from app.schemas.responses import DataResponse, ErrorResponse
from app.services.auth import hash_password, verify_password, create_token_pair, refresh_access_token


router = APIRouter()


@router.post("/auth/signup", response_model=DataResponse[Customer], status_code=status.HTTP_201_CREATED)
async def create_customer(
    *,
    db: Session = Depends(get_db),
    customer_in: CustomerCreate,
    response: Response
) -> DataResponse:
    """
    Create a new customer with proper response handling and status codes.
    """
    try:
        existing_customer = crud_customer.get_by_email(db=db, email=str(customer_in.email).lower())
        if existing_customer:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return DataResponse.error_response(
                message="Customer with this email already exists",
                data=None
            )

        customer_in.password = hash_password(customer_in.password)
        new_customer = crud_customer.create(db=db, obj_in=customer_in)
        response.status_code = status.HTTP_201_CREATED
        return DataResponse.success_response(
            message="Customer created successfully",
            data=new_customer,
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        response.status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message="Failed to create customer",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/auth/verify_email", response_model=DataResponse)
async def verify_email(
    *,
    db: Session = Depends(get_db),
    verification_in: VerificationRequest,
    response: Response
) -> DataResponse:
    """
    Verify customer email with improved error handling.
    """
    try:
        token = crud_customer.get_verification_token(
            db=db,
            token=verification_in.token,
            type="email"
        )

        if not token:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Verification token not found"
            )

        if token.status != "pending" or token.expires_at < func.now():
            response.status_code = status.HTTP_400_BAD_REQUEST
            return DataResponse.error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Token has expired or is invalid"
            )

        result = crud_customer.verify_token(db=db, db_obj=token)
        if result:
            return DataResponse.success_response(
                message="Email verified successfully"
            )

        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            message="Email verification failed",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Verification process failed: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/auth/login", response_model=DataResponse[TokenResponse])
async def customer_login(
        *,
        login_data: LoginRequest,
        db: Session = Depends(get_db),
        response: Response
) -> DataResponse[TokenResponse]:
    """
    Customer login with enhanced response handling.
    """
    try:
        customer = crud_customer.get_by_email(db, email=login_data.email)

        if not customer:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return DataResponse.error_response(
                message="Invalid credentials",
                data=None,
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        if customer.status != "active":
            response.status_code = status.HTTP_403_FORBIDDEN
            return DataResponse.error_response(
                message="Customer account is not active",
                data=None,
                status_code=status.HTTP_403_FORBIDDEN
            )

        if not verify_password(login_data.password, customer.password):
            response.status_code=status.HTTP_401_UNAUTHORIZED
            return DataResponse.error_response(
                message="Invalid credentials",
                data=None,
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        tokens = create_token_pair(customer.id, customer.email, actor="customer", ver="1",
                                   company_id=login_data.company_id)
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=True,  # only over HTTPS
            samesite="strict"
        )
        return DataResponse.success_response(
            message="Login successful",
            data=TokenResponse(**tokens),
        )

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message="Login failed",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/auth/refresh-token", response_model=DataResponse[TokenResponse])
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    response: Response
) -> DataResponse:
    """
    Refresh access token using refresh token.
    """
    try:
        tokens = refresh_access_token(refresh_data.refresh_token)
        if not tokens:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return DataResponse.error_response(
                message="Invalid credentials",
                data=None,
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=True,  # only over HTTPS
            samesite="strict"
        )
        return DataResponse.success_response(
            message="Login successful",
            data=TokenResponse(**tokens),
        )
    except ValueError as ve:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return DataResponse.error_response(
            message=str(ve),
            data=None,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Login failed: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.put("/auth/logout", response_model=DataResponse)
def logout_customer(
    response: Response
) -> DataResponse:
    """
    Logout customer by clearing the refresh token cookie.
    """
    try:
        response.delete_cookie(key="refresh_token")
        return DataResponse.success_response(
            message="Logged out successfully",
            data=None
        )
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message="Logout failed",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# TODO: Add endpoints for password reset, forgot password, etc.
