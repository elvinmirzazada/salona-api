from datetime import datetime, timezone, date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from pydantic.v1 import UUID4
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import Booking, BookingCreate, BookingUpdate, AvailabilityResponse
from app.services.crud import booking as crud_booking
from app.services.crud import service as crud_service
from app.services.crud import company as crud_company
from app.services.crud import user as crud_user
from app.schemas.schemas import Customer
from app.api.dependencies import get_current_active_customer
from app.schemas.responses import DataResponse


router = APIRouter()


@router.post("", response_model=DataResponse[Booking], status_code=status.HTTP_201_CREATED)
def create_booking(
        *,
        db: Session = Depends(get_db),
        booking_in: BookingCreate,
        current_customer: Customer = Depends(get_current_active_customer),
        response: Response
) -> DataResponse:
    """
    Create a new booking.
    """
    # Verify that the company exists
    selected_company = crud_company.get(db=db, id=booking_in.company_id)
    if not selected_company:
        response.status_code = status.HTTP_404_NOT_FOUND
        raise DataResponse.error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Selected company not found"
        )


    for selected_company_service in booking_in.services:

        # Verify that the service exists and belongs to the company
        company_service = crud_service.get_company_service(db=db, id=selected_company_service.company_service_id)
        if not company_service or company_service.company_id != booking_in.company_id:
            response.status_code = status.HTTP_404_NOT_FOUND
            raise DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Service not found or doesn't belong to this company"
            )

        # # Verify that the user(worker) exists and belongs to the company
        selected_user = crud_user.get(db=db, id=selected_company_service.user_id)
        if not selected_user:
            response.status_code = status.HTTP_404_NOT_FOUND
            raise DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="User not found or doesn't belong to this company"
            )

    # Validate booking times
    if booking_in.start_time < datetime.now(timezone.utc):
        response.status_code = status.HTTP_400_BAD_REQUEST
        raise DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot create booking in the past"
        )
    try:
        booking = crud_booking.create(db=db, obj_in=booking_in, customer_id=current_customer.id)
        response.status_code = status.HTTP_201_CREATED
        return DataResponse.success_response(
            message="",
            data=booking,
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to create booking: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{booking_id}", response_model=DataResponse[Booking])
def get_booking(
        *,
        booking_id: str,
        db: Session = Depends(get_db),
        current_customer: Customer = Depends(get_current_active_customer),
        response: Response
) -> DataResponse:
    """
    Get booking by ID with details.
    """
    booking_id = UUID4(booking_id)
    booking = crud_booking.get(db=db, id=booking_id)
    if not booking:
        response.status_code = status.HTTP_404_NOT_FOUND
        raise DataResponse.error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Booking not found"
        )
    response.status_code = status.HTTP_200_OK
    return DataResponse.success_response(
        message="",
        data=booking,
        status_code=status.HTTP_200_OK
    )


@router.get("", response_model=DataResponse[List[Booking]], status_code=status.HTTP_200_OK)
def get_all_bookings(
        *,
        db: Session = Depends(get_db),
        current_customer: Customer = Depends(get_current_active_customer),
        response: Response
) -> DataResponse:
    """
    Get booking by ID with details.
    """
    bookings = crud_booking.get_all(db=db)
    if not bookings:
        response.status_code = status.HTTP_404_NOT_FOUND
        raise DataResponse.error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Booking not found"
        )
    return DataResponse.success_response(
        message="",
        data=bookings,
        status_code=status.HTTP_200_OK
    )
