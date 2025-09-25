from datetime import datetime, timezone, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic.v1 import UUID4
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import Booking, BookingCreate, BookingUpdate, AvailabilityResponse, CustomerCreate, Customer
from app.services.crud import booking as crud_booking
from app.services.crud import service as crud_service
from app.services.crud import company as crud_company
from app.services.crud import user as crud_user
from app.services.crud import customer as crud_customer
from app.api.dependencies import get_current_active_customer, get_token_payload
from app.schemas.responses import DataResponse
from app.api.dependencies import get_current_customer

from app.services.auth import verify_token
import uuid


router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.post("", response_model=DataResponse[Booking], status_code=status.HTTP_201_CREATED)
def create_booking(
        *,
        db: Session = Depends(get_db),
        booking_in: BookingCreate,
        response: Response,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> DataResponse:
    """
    Create a new booking for both registered and unregistered customers.
    If customer is registered (token provided), use that customer.
    If not, create a new inactive customer using provided customer_info.
    """
    # Try to get customer from token if provided
    customer = None
    if credentials:
        customer = get_current_customer(credentials=credentials)

    # If no valid customer found, create a new inactive one
    if not customer:
        # For unregistered customers, we need customer_info in the booking_in
        if not booking_in.customer_info:
            response.status_code = status.HTTP_400_BAD_REQUEST
            raise DataResponse.error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Customer information required for unregistered booking"
            )

        # Create a new customer from the provided information
        customer_data = CustomerCreate(
            first_name=booking_in.customer_info.first_name,
            last_name=booking_in.customer_info.last_name,
            email=booking_in.customer_info.email,
            phone=booking_in.customer_info.phone,
            password=str(uuid.uuid4())  # Random password for inactive account
        )

        # Check if customer with this email already exists
        existing_customer = crud_customer.get_by_email(db, email=str(customer_data.email))
        if existing_customer:
            customer = existing_customer
        else:
            customer = crud_customer.create(db, obj_in=customer_data)

    # Verify that the company exists
    selected_company = crud_company.get(db=db, id=booking_in.company_id)
    if not selected_company:
        response.status_code = status.HTTP_404_NOT_FOUND
        raise DataResponse.error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Selected company not found"
        )

    # Validate booking times
    if booking_in.start_time < datetime.now(timezone.utc):
        response.status_code = status.HTTP_400_BAD_REQUEST
        raise DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot create booking in the past"
        )

    for selected_company_service in booking_in.services:
        # Verify that the service exists and belongs to the company
        company_service = crud_service.get_service(db=db, service_id=selected_company_service.category_service_id,
                                                   company_id=selected_company.id)
        if not company_service:
            response.status_code = status.HTTP_404_NOT_FOUND
            raise DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Service not found or doesn't belong to this company"
            )

        # Verify that the user(worker) exists and belongs to the company
        selected_user = crud_user.get(db=db, id=selected_company_service.user_id)
        if not selected_user:
            response.status_code = status.HTTP_404_NOT_FOUND
            raise DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="User not found or doesn't belong to this company"
            )

    try:
        booking = crud_booking.create(db=db, obj_in=booking_in, customer_id=customer.id)
        response.status_code = status.HTTP_201_CREATED
        db.commit()
        return DataResponse.success_response(
            message="",
            data=booking,
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        db.rollback()
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
