import time

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.api.dependencies import get_current_active_user, get_current_company_id
from app.db.session import get_db
from app.models import AvailabilityType
from app.schemas import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.responses import DataResponse
from app.schemas.schemas import ResponseMessage, TimeOffCreate, TimeOff, TimeOffUpdate
from app.schemas.schemas import UserCreate
from app.services.auth import hash_password, verify_password, create_token_pair, verify_token
from app.services.crud import user as crud_user
from app.services.crud import user_time_off as crud_time_off

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


@router.post("/auth/login", response_model=DataResponse[TokenResponse])
async def user_login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
) -> DataResponse:
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
    company = crud_user.get_company_by_user(db, user.id)
    # Create token pair
    tokens = create_token_pair(user.id, user.email, actor="user", ver="1", company_id=str(company.company_id) if company else '')
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,  # only over HTTPS
        samesite="none"
    )
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        max_age=tokens['expires_in'],
        httponly=True,
        secure=True,  # only over HTTPS
        samesite="none"
    )

    print(tokens)
    return DataResponse.success_response(data = TokenResponse(**tokens))


@router.put("/auth/logout")
async def logout_user(response: Response):
    """
    Logout professional by clearing the refresh token cookie
    """
    try:
        response.delete_cookie(key="refresh_token")
        response.delete_cookie(key="access_token")
        return ResponseMessage(message="Logged out successfully", status="success")
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ResponseMessage(message=f"Internal server error: {str(e)}", status="error")


@router.get("/me", response_model=DataResponse[User])
async def get_current_user(
    *,
    current_user: User = Depends(get_current_active_user)
) -> DataResponse:
    """
    Get current logged-in user.
    """
    return DataResponse.success_response(data=current_user)


@router.post("/time-offs", response_model=DataResponse[TimeOff], status_code=status.HTTP_201_CREATED)
async def create_time_off(
    *,
    db: Session = Depends(get_db),
    time_off_in: TimeOffCreate,
    response: Response,
    company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Create a new time off period for the current user.
    """
    try:
        # Check for overlapping time offs
        has_overlap = crud_time_off.check_overlapping_time_offs(
            db=db,
            user_id=time_off_in.user_id,
            start_date=time_off_in.start_date,
            end_date=time_off_in.end_date
        )

        if has_overlap:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return DataResponse.error_response(
                message="The time off period overlaps with existing ones",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Create the time off
        time_off = crud_time_off.create(
            db=db,
            obj_in=time_off_in,
            company_id=company_id
        )

        return DataResponse.success_response(
            message="Time off created successfully",
            data=time_off,
            status_code=status.HTTP_201_CREATED
        )
    except ValueError as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to create time off: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/time-offs", response_model=DataResponse[List[TimeOff]], status_code=status.HTTP_200_OK)
async def get_all_user_time_offs(
    *,
    db: Session = Depends(get_db),
    start_date: datetime = Query(datetime.today(), description="Filter time offs that end after this date"),
    availability_type: AvailabilityType = Query(AvailabilityType.WEEKLY, description="Type of availability check: daily, weekly, or monthly"),
    response: Response,
    company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Get all time offs for the current user with optional date filtering.
    """
    try:
        end_date = start_date + timedelta(
                days=1 if availability_type == AvailabilityType.DAILY else
                     7 if availability_type == AvailabilityType.WEEKLY else 31
            )
        time_offs = crud_time_off.get_user_time_offs(
            db=db,
            company_id=company_id,
            start_date=start_date,
            end_date=end_date
        )

        return DataResponse.success_response(
            data=time_offs,
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to retrieve time offs: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.put("/time-offs/{time_off_id}", response_model=DataResponse[TimeOff], status_code=status.HTTP_200_OK)
async def update_time_off(
    *,
    time_off_id: str,
    db: Session = Depends(get_db),
    time_off_in: TimeOffUpdate,
    response: Response,
    current_user: User = Depends(get_current_active_user)
) -> DataResponse:
    """
    Update an existing time off period.
    """
    try:
        # Get the time off by ID
        time_off = crud_time_off.get(db=db, time_off_id=time_off_id)
        if not time_off:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                message="Time off not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Check if the time off belongs to the current user
        if str(time_off.user_id) != str(current_user.id):
            response.status_code = status.HTTP_403_FORBIDDEN
            return DataResponse.error_response(
                message="You don't have permission to update this time off",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Determine the new start and end dates for overlap check
        start_date = time_off_in.start_date if time_off_in.start_date is not None else time_off.start_date
        end_date = time_off_in.end_date if time_off_in.end_date is not None else time_off.end_date

        # Check for overlapping time offs
        has_overlap = crud_time_off.check_overlapping_time_offs(
            db=db,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            exclude_id=time_off_id
        )

        if has_overlap:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return DataResponse.error_response(
                message="The updated time off period overlaps with existing ones",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Update the time off
        updated_time_off = crud_time_off.update(
            db=db,
            db_obj=time_off,
            obj_in=time_off_in
        )

        return DataResponse.success_response(
            message="Time off updated successfully",
            data=updated_time_off,
            status_code=status.HTTP_200_OK
        )
    except ValueError as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to update time off: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/time-offs/{time_off_id}", response_model=DataResponse, status_code=status.HTTP_200_OK)
async def delete_time_off(
    *,
    time_off_id: str,
    db: Session = Depends(get_db),
    response: Response,
    current_user: User = Depends(get_current_active_user)
) -> DataResponse:
    """
    Delete a time off period.
    """
    # Get the time off by ID
    time_off = crud_time_off.get(db=db, time_off_id=time_off_id)
    if not time_off:
        response.status_code = status.HTTP_404_NOT_FOUND
        return DataResponse.error_response(
            message="Time off not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # Check if the time off belongs to the current user
    if str(time_off.user_id) != str(current_user.id):
        response.status_code = status.HTTP_403_FORBIDDEN
        return DataResponse.error_response(
            message="You don't have permission to delete this time off",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Delete the time off
    deleted = crud_time_off.delete(db=db, time_off_id=time_off_id)
    if not deleted:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message="Failed to delete time off",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return DataResponse.success_response(
        message="Time off deleted successfully",
        status_code=status.HTTP_200_OK
    )


@router.post("/auth/refresh-token", response_model=DataResponse[TokenResponse])
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
) -> DataResponse:
    """
    Refresh access and refresh tokens using the refresh token cookie.
    """
    try:
        # Get the refresh token from the request cookies
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found"
            )

        # Verify and decode the refresh token
        payload = verify_token(refresh_token, "refresh")
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Extract user data from payload
        user_id = payload.get("sub")
        email = payload.get("email")
        company_id = payload.get("company_id")

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Create new tokens
        new_tokens = create_token_pair(
            id=int(user_id),
            email=email,
            actor="user",
            ver="1",
            company_id=company_id
        )

        # Set new cookies
        response.set_cookie(
            key="refresh_token",
            value=new_tokens["refresh_token"],
            httponly=True,
            secure=True,
            samesite="strict"
        )
        response.set_cookie(
            key="access_token",
            value=new_tokens["access_token"],
            max_age=new_tokens['expires_in'],
            httponly=True,
            secure=True,
            samesite="strict"
        )

        return DataResponse.success_response(data=TokenResponse(**new_tokens))

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {str(e)}"
        )


@router.post("/auth/verify-token", response_model=DataResponse[dict])
async def verify_access_token(
    request: Request,
    response: Response
) -> DataResponse:
    """
    Verify the access token and return the token data.
    """
    try:
        # Get the access token from the request cookies
        access_token = request.cookies.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token not found"
            )

        # Verify and decode the access token
        payload = verify_token(access_token, "access")
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token"
            )

        # Return token validity info
        return DataResponse.success_response(data={
            "valid": True,
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "company_id": payload.get("company_id"),
            "expires_at": payload.get("exp")
        })

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify token: {str(e)}"
        )
