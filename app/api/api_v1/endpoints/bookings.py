from datetime import datetime, timezone, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic.v1 import UUID4
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas import User
from app.schemas.schemas import Booking, BookingCreate, BookingUpdate, AvailabilityResponse, CustomerCreate
from app.services.crud import booking as crud_booking
from app.services.crud import service as crud_service
from app.services.crud import company as crud_company
from app.services.crud import user as crud_user
from app.services.crud import customer as crud_customer
from app.api.dependencies import get_current_company_id, get_token_payload
from app.schemas.responses import DataResponse
from app.api.dependencies import get_current_customer
from app.models import BookingServices, BookingStatus

from app.services.auth import verify_token
import uuid


router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.post("", response_model=DataResponse[Booking], status_code=status.HTTP_201_CREATED)
async def create_booking(
        *,
        db: Session = Depends(get_db),
        booking_in: BookingCreate,
        response: Response
) -> DataResponse:
    """
    Create a new booking for both registered and unregistered customers.
    If customer is registered (token provided), use that customer.
    If not, create a new inactive customer using provided customer_info.
    """
    # Try to get customer from token if provided
    customer = None
    # print(credentials)
    # if credentials:
    #     customer = get_current_customer(credentials=credentials, db=db)

    print(booking_in.__dict__)

    # If no valid customer found, create a new inactive one
    if not customer:
        # For unregistered customers, we need customer_info in the booking_in
        if not booking_in.customer_info:
            response.status_code = status.HTTP_400_BAD_REQUEST
            raise DataResponse.error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Customer information required for unregistered booking"
            )
        if booking_in.customer_info.id:
            # If customer_info contains an ID, try to fetch that customer
            existing_customer = crud_customer.get(db, id=booking_in.customer_info.id)
            if existing_customer:
                customer = existing_customer
            else:
                response.status_code = status.HTTP_404_NOT_FOUND
                raise DataResponse.error_response(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Customer with provided ID not found"
                )
            # If we found the customer by ID, we can skip creating a new one
            booking_in.customer_info = None  # Clear to avoid confusion later

        # Create a new customer from the provided information
        if booking_in.customer_info:
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
        # current_customer: Customer = Depends(get_current_active_customer),
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
async def get_all_bookings(
        *,
        db: Session = Depends(get_db),
        company_id: str = Depends(get_current_company_id),
        start_date: Optional[date] = Query(None, description="Start date in YYYY-MM-DD format"),
        end_date: Optional[date] = Query(None, description="End date in YYYY-MM-DD format")
) -> DataResponse:
    """
    Get bookings with details for a company within a date range.
    """

    if not start_date:
        start_date = (datetime.now() - timedelta(days=datetime.now().weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = (datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(days=7)).replace(hour=23, minute=59, second=59, microsecond=999999)

    bookings: List[Booking] = crud_booking.get_all_bookings_in_range_by_company(db=db,
                                                                 company_id=company_id,
                                                                 start_date=start_date,
                                                                 end_date=end_date)
    result = []
    for booking in bookings:
        tmp = Booking(**booking.__dict__)
        for service in booking.booking_services:
            tmp.user_ids.add(str(service.user_id))
        result.append(tmp)
    if not result:
        return DataResponse.success_response(
            message="No bookings found",
            data=[],
            status_code=status.HTTP_200_OK
        )

    return DataResponse.success_response(
        message="",
        data=result,
        status_code=status.HTTP_200_OK
    )


@router.post("/users/create_booking", response_model=DataResponse[Booking], status_code=status.HTTP_201_CREATED)
async def create_booking_by_user(
        *,
        db: Session = Depends(get_db),
        booking_in: BookingCreate,
        response: Response,
        company_id: str = Depends(get_current_company_id),

) -> DataResponse:
    """
    Create a new booking for both registered and unregistered customers.
    If customer is registered (token provided), use that customer.
    If not, create a new inactive customer using provided customer_info.
    """
    # Try to get customer from token if provided
    customer = None
    if not booking_in.company_id:
        booking_in.company_id = company_id


    # For unregistered customers, we need customer_info in the booking_in
    if not booking_in.customer_info:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Customer information required for unregistered booking"
        )
    if booking_in.customer_info.id:
        # If customer_info contains an ID, try to fetch that customer
        existing_customer = crud_customer.get(db, id=booking_in.customer_info.id)
        if existing_customer:
            customer = existing_customer
        else:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Customer with provided ID not found"
            )
        # If we found the customer by ID, we can skip creating a new one
        booking_in.customer_info = None  # Clear to avoid confusion later

    # Create a new customer from the provided information
    if booking_in.customer_info:
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
        return DataResponse.error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Selected company not found"
        )

    # Validate booking times
    if booking_in.start_time < datetime.now(timezone.utc):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot create booking in the past"
        )

    for selected_company_service in booking_in.services:
        # Verify that the service exists and belongs to the company
        company_service = crud_service.get_service(db=db, service_id=selected_company_service.category_service_id,
                                                   company_id=selected_company.id)
        if not company_service:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Service not found or doesn't belong to this company"
            )

        # Verify that the user(worker) exists and belongs to the company
        selected_user = crud_user.get(db=db, id=selected_company_service.user_id)
        if not selected_user:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                data = None,
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


@router.put("/{booking_id}", response_model=DataResponse[Booking], status_code=status.HTTP_200_OK)
async def update_booking(
        *,
        booking_id: str,
        db: Session = Depends(get_db),
        booking_update: BookingUpdate,
        response: Response,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Update a booking by ID.
    Can update start time, notes, status, and services.
    """
    try:
        booking_uuid = UUID4(booking_id)
    except ValueError:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid booking ID format"
        )

    # Get the existing booking
    existing_booking = crud_booking.get(db=db, id=booking_uuid)
    if not existing_booking:
        response.status_code = status.HTTP_404_NOT_FOUND
        return DataResponse.error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Booking not found"
        )

    # Verify that the booking belongs to the company
    if str(existing_booking.company_id) != company_id:
        response.status_code = status.HTTP_403_FORBIDDEN
        return DataResponse.error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You don't have permission to update this booking"
        )

    # Validate new start time if provided
    if booking_update.start_time and booking_update.start_time < datetime.now(timezone.utc):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot schedule booking in the past"
        )

    # Validate services if provided
    if booking_update.services:
        for service_request in booking_update.services:
            # Verify that the service exists and belongs to the company
            company_service = crud_service.get_service(
                db=db,
                service_id=service_request.category_service_id,
                company_id=company_id
            )
            if not company_service:
                response.status_code = status.HTTP_404_NOT_FOUND
                return DataResponse.error_response(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Service not found or doesn't belong to this company"
                )

            # Verify that the user(worker) exists and belongs to the company
            selected_user = crud_user.get(db=db, id=service_request.user_id)
            if not selected_user:
                response.status_code = status.HTTP_404_NOT_FOUND
                return DataResponse.error_response(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="User not found"
                )

    try:
        updated_booking = crud_booking.update(
            db=db,
            db_obj=existing_booking,
            obj_in=booking_update
        )
        response.status_code = status.HTTP_200_OK
        return DataResponse.success_response(
            message="Booking updated successfully",
            data=updated_booking,
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to update booking: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/{booking_id}", response_model=DataResponse[Booking], status_code=status.HTTP_200_OK)
async def delete_booking(
        *,
        booking_id: str,
        db: Session = Depends(get_db),
        response: Response,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Cancel a booking by ID (marks as cancelled instead of deleting).
    """
    try:
        booking_uuid = UUID4(booking_id)
    except ValueError:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid booking ID format"
        )

    # Get the existing booking
    existing_booking = crud_booking.get(db=db, id=booking_uuid)
    if not existing_booking:
        response.status_code = status.HTTP_404_NOT_FOUND
        return DataResponse.error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Booking not found"
        )

    # Verify that the booking belongs to the company
    if str(existing_booking.company_id) != company_id:
        response.status_code = status.HTTP_403_FORBIDDEN
        return DataResponse.error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You don't have permission to cancel this booking"
        )

    try:
        # Use the CRUD cancel function to mark the booking as cancelled
        cancelled_booking = crud_booking.cancel(db=db, booking_id=booking_uuid)
        if not cancelled_booking:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Booking not found"
            )

        db.commit()

        response.status_code = status.HTTP_200_OK
        return DataResponse.success_response(
            message="Booking cancelled successfully",
            data=cancelled_booking,
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to cancel booking: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.put("/{booking_id}/confirm", response_model=DataResponse[Booking], status_code=status.HTTP_200_OK)
async def confirm_booking(
        *,
        booking_id: str,
        db: Session = Depends(get_db),
        response: Response,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Confirm a booking by setting its status to CONFIRMED.
    """
    try:
        booking_uuid = UUID4(booking_id)
    except ValueError:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid booking ID format"
        )

    # Get the existing booking
    existing_booking = crud_booking.get(db=db, id=booking_uuid)
    if not existing_booking:
        response.status_code = status.HTTP_404_NOT_FOUND
        return DataResponse.error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Booking not found"
        )

    # Verify that the booking belongs to the company
    if str(existing_booking.company_id) != company_id:
        response.status_code = status.HTTP_403_FORBIDDEN
        return DataResponse.error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You don't have permission to confirm this booking"
        )

    # Check if booking is already cancelled
    if existing_booking.status == BookingStatus.CANCELLED:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot confirm a cancelled booking"
        )

    # Check if booking is already completed
    if existing_booking.status == BookingStatus.COMPLETED:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot confirm a completed booking"
        )

    try:
        # Use the CRUD confirm function to mark the booking as confirmed
        confirmed_booking = crud_booking.confirm(db=db, booking_id=booking_uuid)
        if not confirmed_booking:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Booking not found"
            )

        db.commit()

        response.status_code = status.HTTP_200_OK
        return DataResponse.success_response(
            message="Booking confirmed successfully",
            data=confirmed_booking,
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to confirm booking: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
