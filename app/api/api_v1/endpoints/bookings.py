from collections import defaultdict
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic.v1 import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.redis_client import publish_event
from app.schemas import CompanyNotificationCreate
from app.services.notification_service import notification_service
from app.services.email_service import email_service
from app.schemas.schemas import Booking, BookingCreate, BookingUpdate, AvailabilityResponse, CustomerCreate
from app.services.crud import booking as crud_booking
from app.services.crud import service as crud_service
from app.services.crud import company as crud_company
from app.services.crud import user as crud_user
from app.services.crud import customer as crud_customer
from app.api.dependencies import get_current_company_id, get_token_payload
from app.schemas.responses import DataResponse
from app.api.dependencies import get_current_customer
from app.models import BookingServices, BookingStatus, NotificationType, CompanyUsers, CompanyRoleType, Users

from app.services.auth import verify_token
import uuid
import json


router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.get("", response_model=DataResponse[List[Booking]], status_code=status.HTTP_200_OK)
async def get_all_bookings(
        *,
        db: AsyncSession = Depends(get_db),
        company_id: str = Depends(get_current_company_id),
        start_date: Optional[date] = Query(None, description="Start date in YYYY-MM-DD format"),
        end_date: Optional[date] = Query(None, description="End date in YYYY-MM-DD format")
) -> DataResponse:
    """
    Get bookings with details for a company within a date range.
    """
    if not company_id:
        raise DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Company ID is required"
        )
    if not start_date:
        # Get timezone-aware datetime for start of week
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).date()
    if not end_date:
        # Get timezone-aware datetime for end of week
        now = datetime.now(timezone.utc)
        end_date = (now - timedelta(days=now.weekday()) + timedelta(days=7)).replace(hour=23, minute=59, second=59, microsecond=999999).date()

    bookings: List[Booking] = await crud_booking.get_all_bookings_in_range_by_company(db=db,
                                                                 company_id=company_id,
                                                                 start_date=start_date,
                                                                 end_date=end_date)

    if not bookings:
        return DataResponse.success_response(
            message="No bookings found",
            data=[],
            status_code=status.HTTP_200_OK
        )

    return DataResponse.success_response(
        message="",
        data=bookings,
        status_code=status.HTTP_200_OK
    )


@router.post("/users/create_booking", response_model=DataResponse[Booking], status_code=status.HTTP_201_CREATED)
async def create_booking_by_user(
        *,
        db: AsyncSession = Depends(get_db),
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
        existing_customer = await crud_customer.get(db, id=booking_in.customer_info.id)
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
        existing_customer = await crud_customer.get_by_email(db, email=str(customer_data.email))
        if existing_customer:
            customer = existing_customer
        else:
            customer = await crud_customer.create(db, obj_in=customer_data)

    # Verify that the company exists
    selected_company = await crud_company.get(db=db, id=booking_in.company_id)
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

    # Calculate the start and end time for each service to check staff availability
    current_start_time = booking_in.start_time
    
    for selected_company_service in booking_in.services:
        # Verify that the service exists and belongs to the company
        company_service = await crud_service.get_service(db=db, service_id=selected_company_service.category_service_id,
                                                   company_id=selected_company.id)
        if not company_service:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Service not found or doesn't belong to this company"
            )

        # Verify that the user(worker) exists and belongs to the company
        selected_user = await crud_user.get(db=db, id=selected_company_service.user_id)
        if not selected_user:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                data = None,
                status_code=status.HTTP_404_NOT_FOUND,
                message="User not found or doesn't belong to this company"
            )
        
        # Calculate end time for this service
        service_end_time = current_start_time + timedelta(minutes=company_service.duration)
        
        # Check if the staff member is available for this service time slot
        is_available, conflict_message = await crud_booking.check_staff_availability(
            db=db,
            user_id=selected_company_service.user_id,
            start_time=current_start_time,
            end_time=service_end_time
        )
        
        if not is_available:
            response.status_code = status.HTTP_409_CONFLICT
            return DataResponse.error_response(
                status_code=status.HTTP_409_CONFLICT,
                message=conflict_message
            )
        
        # Move to the next service start time
        current_start_time = service_end_time

    try:
        booking = await crud_booking.create(db=db, obj_in=booking_in, customer_id=customer.id)
        response.status_code = status.HTTP_201_CREATED
        # await publish_event('booking_created', str({'info': f"A new booking has been created by {customer.first_name} {customer.last_name}"}))

        # Create confirmation notification for the assigned staff member
        booking_data = json.dumps({
            'booking_id': str(booking.id),
            'company_id': str(booking.company_id)
        }).encode('utf-8')
        
        res = await notification_service.create_notification(
            db=db,
            notification_request=CompanyNotificationCreate(
                company_id=booking_in.company_id,
                type=NotificationType.BOOKING_CREATED,
                message=f"A new booking has been created by {customer.first_name} {customer.last_name}",
                data=booking_data
            )
        )
        booking = Booking.model_validate(booking)
        return DataResponse.success_response(
            message="",
            data=booking,
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        await db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to create booking: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put("/{booking_id}", response_model=DataResponse[Booking], status_code=status.HTTP_200_OK)
async def update_booking(
        *,
        db: AsyncSession = Depends(get_db),
        booking_id: str,
        booking_in: BookingUpdate,
        response: Response,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Update booking information.
    Can update status, start_time, end_time, services, or notes.
    """
    try:
        # Get the existing booking
        booking = await crud_booking.get(db=db, id=booking_id)
        if not booking:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Booking not found"
            )

        # Check if booking belongs to the company
        if str(booking.company_id) != company_id:
            response.status_code = status.HTTP_403_FORBIDDEN
            return DataResponse.error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message="You don't have permission to update this booking"
            )

        # If updating time, validate it's not in the past
        if booking_in.start_time and booking_in.start_time < datetime.now(timezone.utc):
            response.status_code = status.HTTP_400_BAD_REQUEST
            return DataResponse.error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Cannot update booking time to the past"
            )

        # If services are being updated, validate them
        if booking_in.services:
            current_start_time = booking_in.start_time or booking.start_at

            for selected_company_service in booking_in.services:
                # Verify service exists and belongs to company
                company_service = await crud_service.get_service(
                    db=db,
                    service_id=selected_company_service.category_service_id,
                    company_id=company_id
                )
                if not company_service:
                    response.status_code = status.HTTP_404_NOT_FOUND
                    return DataResponse.error_response(
                        status_code=status.HTTP_404_NOT_FOUND,
                        message="Service not found or doesn't belong to this company"
                    )

                # Verify user exists and belongs to company
                selected_user = await crud_user.get(db=db, id=selected_company_service.user_id)
                if not selected_user:
                    response.status_code = status.HTTP_404_NOT_FOUND
                    return DataResponse.error_response(
                        data=None,
                        status_code=status.HTTP_404_NOT_FOUND,
                        message="User not found or doesn't belong to this company"
                    )

                # Calculate end time for this service
                service_end_time = current_start_time + timedelta(minutes=company_service.duration)

                # Check staff availability (excluding current booking)
                is_available, conflict_message = await crud_booking.check_staff_availability(
                    db=db,
                    user_id=selected_company_service.user_id,
                    start_time=current_start_time,
                    end_time=service_end_time,
                    exclude_booking_id=booking_id
                )

                if not is_available:
                    response.status_code = status.HTTP_409_CONFLICT
                    return DataResponse.error_response(
                        status_code=status.HTTP_409_CONFLICT,
                        message=conflict_message
                    )

                current_start_time = service_end_time

        # Update the booking
        updated_booking = await crud_booking.update(db=db, db_obj=booking, obj_in=booking_in)

        # Create notification for status change
        if booking_in.status and booking_in.status != booking.status:
            booking_data = json.dumps({
                'booking_id': str(booking.id),
                'company_id': str(booking.company_id),
                'old_status': str(booking.status),
                'new_status': str(booking_in.status)
            }).encode('utf-8')

            await notification_service.create_notification(
                db=db,
                notification_request=CompanyNotificationCreate(
                    company_id=company_id,
                    type=NotificationType.BOOKING_UPDATED,
                    message=f"Booking status changed from {booking.status} to {booking_in.status}",
                    data=booking_data
                )
            )

        return DataResponse.success_response(
            message="Booking updated successfully",
            data=updated_booking,
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        await db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to update booking: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.patch("/{booking_id}/no-show", response_model=DataResponse[Booking], status_code=status.HTTP_200_OK)
async def mark_booking_no_show(
        *,
        booking_id: str,
        db: AsyncSession = Depends(get_db),
        response: Response,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Mark a booking as NO_SHOW when the customer doesn't show up.
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
    existing_booking = await crud_booking.get(db=db, id=booking_uuid)
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
            message="You don't have permission to modify this booking"
        )

    # Check if booking is already cancelled
    if existing_booking.status == BookingStatus.CANCELLED:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot mark a cancelled booking as no-show"
        )

    # Check if booking is already completed
    if existing_booking.status == BookingStatus.COMPLETED:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot mark a completed booking as no-show"
        )

    # Check if booking is already marked as no-show
    if existing_booking.status == BookingStatus.NO_SHOW:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Booking is already marked as no-show"
        )

    try:
        # Use the CRUD no_show function to mark the booking as no-show
        no_show_booking = await crud_booking.no_show(db=db, booking_id=booking_uuid)
        if not no_show_booking:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Booking not found"
            )

        await db.commit()
        response.status_code = status.HTTP_200_OK
        return DataResponse.success_response(
            message="Booking marked as no-show successfully",
            data=no_show_booking,
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        await db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to mark booking as no-show: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/{booking_id}", response_model=DataResponse[Booking], status_code=status.HTTP_200_OK)
async def delete_booking(
        *,
        booking_id: str,
        db: AsyncSession = Depends(get_db),
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
    existing_booking = await crud_booking.get(db=db, id=booking_uuid)
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
        cancelled_booking = await crud_booking.cancel(db=db, booking_id=booking_uuid)
        if not cancelled_booking:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Booking not found"
            )

        await db.commit()

        company = await crud_company.get(db, id=cancelled_booking.company_id)

        email_service.send_booking_cancellation_to_customer_email(
            to_email=cancelled_booking.customer.email,
            customer_name=cancelled_booking.customer.first_name,
            company_name=company.name,
            booking_date=cancelled_booking.start_at.isoformat(),
            services=[service.category_service.name for service in cancelled_booking.booking_services],
            company_id=company.id
        )

        response.status_code = status.HTTP_200_OK
        return DataResponse.success_response(
            message="Booking cancelled successfully",
            data=cancelled_booking,
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        await db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to cancel booking: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.patch("/{booking_id}/confirm", response_model=DataResponse[Booking], status_code=status.HTTP_200_OK)
async def confirm_booking(
        *,
        booking_id: str,
        db: AsyncSession = Depends(get_db),
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
    existing_booking = await crud_booking.get(db=db, id=booking_uuid)
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
        confirmed_booking = await crud_booking.confirm(db=db, booking_id=booking_uuid)
        if not confirmed_booking:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Booking not found"
            )

        await db.commit()
        company = await crud_company.get(db, id=confirmed_booking.company_id)

        # Get company address for calendar location
        from app.models.models import CompanyAddresses
        from sqlalchemy import select
        stmt = select(CompanyAddresses).filter(
            CompanyAddresses.company_id == confirmed_booking.company_id
        )
        result = await db.execute(stmt)
        company_address = result.scalar_one_or_none()

        # Format location string
        location = None
        if company_address:
            location = f"{company_address.address}, {company_address.city}, {company_address.country}"
            if company_address.zip:
                location = f"{company_address.address}, {company_address.city}, {company_address.zip}, {company_address.country}"

        email_service.send_booking_confirmation_to_customer_email(
            to_email=confirmed_booking.customer.email,
            customer_name=confirmed_booking.customer.first_name,
            company_name=company.name,
            booking_date=confirmed_booking.start_at.isoformat(),
            services=[service.category_service.name for service in confirmed_booking.booking_services],
            start_datetime=confirmed_booking.start_at,
            end_datetime=confirmed_booking.end_at,
            location=location
        )
        response.status_code = status.HTTP_200_OK
        return DataResponse.success_response(
            message="Booking confirmed successfully",
            data=confirmed_booking,
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        await db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to confirm booking: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.patch("/{booking_id}/complete", response_model=DataResponse[Booking], status_code=status.HTTP_200_OK)
async def complete_booking(
        *,
        booking_id: str,
        db: AsyncSession = Depends(get_db),
        response: Response,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Complete a booking by setting its status to COMPLETED.
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
    existing_booking = await crud_booking.get(db=db, id=booking_uuid)
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
            message="You don't have permission to complete this booking"
        )

    # Check if booking is already cancelled
    if existing_booking.status == BookingStatus.CANCELLED:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot complete a cancelled booking"
        )

    # Check if booking is already completed
    if existing_booking.status == BookingStatus.COMPLETED:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Booking is already completed"
        )

    try:
        # Use the CRUD complete function to mark the booking as completed
        completed_booking = await crud_booking.complete(db=db, booking_id=booking_uuid)
        if not completed_booking:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Booking not found"
            )

        await db.commit()
        company = await crud_company.get(db, id=completed_booking.company_id)
        email_service.send_booking_completed_to_customer_email(
            to_email=completed_booking.customer.email,
            customer_name=completed_booking.customer.first_name,
            company_name=company.name,
            booking_date=completed_booking.start_at.isoformat(),
            services=[service.category_service.name for service in completed_booking.booking_services],
            total_price=completed_booking.total_price / 100.0
        )
        response.status_code = status.HTTP_200_OK
        return DataResponse.success_response(
            message="Booking completed successfully",
            data=completed_booking,
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        await db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to complete booking: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
