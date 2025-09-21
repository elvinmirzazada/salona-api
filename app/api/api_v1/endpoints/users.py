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


# @router.get("/me", response_model=Professional)
# async def get_current_professional_info(
#     current_professional: Professional = Depends(get_current_active_professional)
# ) -> Professional:
#     """
#     Get current professional's information from JWT token.
#     """
#     return current_professional
#
#
# @router.get("/{professional_id}", response_model=Professional)
# async def get_professional(
#     professional_id: int,
#     db: Session = Depends(get_db),
#     current_professional: Professional = Depends(get_current_active_professional)
# ) -> Professional:
#     """
#     Get professional by ID. Requires authentication.
#     """
#     # Check if the requesting professional is trying to access their own data or has permission
#     if current_professional.id != professional_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to access this professional's information"
#         )
#
#     professional = crud_professional.get(db=db, id=professional_id)
#     if not professional:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Professional not found"
#         )
#     return professional
#
#
# @router.put("/{professional_id}", response_model=Professional)
# async def update_professional(
#     *,
#     db: Session = Depends(get_db),
#     professional_id: int,
#     professional_in: ProfessionalUpdate,
#     current_professional: Professional = Depends(get_current_active_professional)
# ) -> Professional:
#     """
#     Update professional. Requires authentication.
#     """
#     # Check if the requesting professional is trying to update their own data
#     if current_professional.id != professional_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to update this professional's information"
#         )
#
#     professional = crud_professional.get(db=db, id=professional_id)
#     if not professional:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Professional not found"
#         )
#
#     professional = crud_professional.update(db=db, db_obj=professional, obj_in=professional_in)
#     return professional
#
#
# @router.get("/mobile/{mobile_number}", response_model=Professional)
# async def get_professional_by_mobile(
#     mobile_number: str,
#     db: Session = Depends(get_db),
#     current_professional: Professional = Depends(get_current_active_professional)
# ) -> Professional:
#     """
#     Get professional by mobile number. Requires authentication.
#     """
#     professional = crud_professional.get_by_mobile(db=db, mobile_number=mobile_number)
#     if not professional:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Professional not found"
#         )
#
#     # Check if the requesting professional is trying to access their own data
#     if current_professional.id != professional.id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to access this professional's information"
#         )
#
#     return professional
#
#
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

#
# @router.post("/refresh-token", response_model=TokenResponse)
# async def refresh_token(
#     refresh_data: RefreshTokenRequest
# ) -> TokenResponse:
#     """
#     Refresh access token using refresh token.
#     """
#     tokens = refresh_access_token(refresh_data.refresh_token)
#     if not tokens:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid refresh token"
#         )
#
#     return TokenResponse(**tokens)
#
#
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


@router.get("/{user_id}/availability", response_model=DataResponse[AvailabilityResponse])
async def get_user_availability(
        *,
        user_id: str,
        availability_type: AvailabilityType = Query(..., description="Type of availability check: daily, weekly, or monthly"),
        date_from: date = Query(..., description="Start date for availability check"),
        response: Response,
        db: Session = Depends(get_db)
) -> DataResponse[AvailabilityResponse]:
    """
    Get user availability for a specific time range.
    - daily: Shows available time slots for a specific date
    - weekly: Shows available time slots for a week starting from date_from
    - monthly: Shows available time slots for the month containing date_from
    """
    try:
        # Get user's regular availability
        availabilities = crud_availability.get_user_availabilities(db, user_id=user_id)
        if not availabilities:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                message="No availability schedule found for this user",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Get user's time-offs
        time_offs = crud_availability.get_user_time_offs(
            db,
            user_id=user_id,
            start_date=date_from,
            end_date=date_from + timedelta(
                days=1 if availability_type == AvailabilityType.DAILY else
                     7 if availability_type == AvailabilityType.WEEKLY else 31
            )
        )

        # Get existing bookings
        bookings = crud_booking.get_user_bookings_in_range(
            db,
            user_id=user_id,
            start_date=date_from,
            end_date=date_from + timedelta(
                days=1 if availability_type == AvailabilityType.DAILY else
                     7 if availability_type == AvailabilityType.WEEKLY else 31
            )
        )

        if availabilities:
            # Calculate availability based on working hours, time-offs, and existing bookings
            availability = crud_availability.calculate_availability(
                availabilities=availabilities,
                time_offs=time_offs,
                bookings=bookings,
                availability_type=availability_type,
                date_from=date_from
            )

            return DataResponse.success_response(
                data=availability,
                message="Availability retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        else:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                message="No availability schedule found for this user",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to retrieve availability: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
