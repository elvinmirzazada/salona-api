import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone, date, timedelta
from typing import List
from pydantic.v1 import UUID4
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import NotificationType
from app.schemas import CompanyNotificationCreate
from app.schemas.responses import DataResponse
from app.schemas.schemas import Booking, BookingCreate, AvailabilityResponse, CustomerCreate
from app.schemas.schemas import (CompanyCategoryWithServicesResponse, CompanyUser, AvailabilityType)
from app.services.crud import booking as crud_booking
from app.services.crud import company as crud_company
from app.services.crud import customer as crud_customer
from app.services.crud import service as crud_service
from app.services.crud import user as crud_user
from app.services.crud import user_availability as crud_user_availability
from app.services.email_service import email_service
from app.services.notification_service import notification_service

router = APIRouter()


@router.get("/companies/{company_slug}/services", response_model=DataResponse[List[CompanyCategoryWithServicesResponse]])
async def get_company_services(
    company_slug: str,
    db: AsyncSession = Depends(get_db)
) -> DataResponse:
    """
    Get service by company ID with details.
    """
    company = await crud_company.get_by_slug(db=db, slug=company_slug)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    company_id = str(company.id)
    services = await crud_service.get_company_services(db=db, company_id=company_id)
    if not services:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    return DataResponse.success_response(
        data=services,
        message="Services fetched successfully"
    )


@router.get("/companies/{company_slug}/staff", response_model=DataResponse[List[CompanyUser]])
async def get_company_users(
    company_slug: str,
    db: Session = Depends(get_db)
) -> DataResponse:
    """
    Get users by company ID with details.
    """
    company = await crud_company.get_by_slug(db=db, slug=company_slug)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    company_id = str(company.id)
    users = await crud_user.get_company_users(db=db, company_id=company_id)
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    return DataResponse.success_response(
        data=users,
        message="Services fetched successfully"
    )


@router.get("/companies/{company_slug}/users/{user_id}/availability", response_model=DataResponse[AvailabilityResponse])
async def get_user_availability(
        *,
        user_id: str,
        availability_type: AvailabilityType = Query(..., description="Type of availability check: daily, weekly, or monthly"),
        date_from: date = Query(..., description="Start date for availability check"),
        service_ids: List[str] = Query(None, description="List of service IDs to calculate availability based on combined service duration"),
        response: Response,
        db: Session = Depends(get_db),
        company_slug: str
) -> DataResponse[AvailabilityResponse]:
    """
    Get user availability for a specific time range.
    - daily: Shows available time slots for a specific date
    - weekly: Shows available time slots for a week starting from date_from
    - monthly: Shows available time slots for the month containing date_from

    If service_ids are provided, the last available slot will be calculated based on the total duration of all services.
    """
    try:
        company = await crud_company.get_by_slug(db=db, slug=company_slug)
        if not company:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                message="Company not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        company_id = str(company.id)
        company_timezone = company.timezone or "UTC"

        # Calculate total service duration if service_ids are provided
        service_duration_minutes = None
        if service_ids:
            total_duration = 0
            for service_id in service_ids:
                service = await crud_service.get_service(db=db, service_id=service_id, company_id=company_id)
                if service:
                    total_duration += service.duration
            service_duration_minutes = total_duration if total_duration > 0 else None

        # Get user's regular availability
        availabilities = await crud_company.get_company_user_availabilities(db, user_id=user_id, company_id=company_id)
        if not availabilities:
            response.status_code = status.HTTP_200_OK
            return DataResponse.success_response(
                data=AvailabilityResponse(
                    user_id=None,
                    availability_type=availability_type,
                    daily=None
                ),
                message="No availability schedule found for this user"
            )

        # Get user's time-offs
        time_offs = await crud_company.get_company_user_time_offs(
            db,
            user_id=user_id,
            company_id=company_id,
            start_date=date_from,
            end_date=date_from + timedelta(
                days=1 if availability_type == AvailabilityType.DAILY else
                     7 if availability_type == AvailabilityType.WEEKLY else 31
            )
        )

        # Get existing bookings
        bookings = await crud_booking.get_user_bookings_in_range(
            db,
            user_id=user_id,
            start_date=date_from,
            end_date=date_from + timedelta(
                days=1 if availability_type == AvailabilityType.DAILY else
                     7 if availability_type == AvailabilityType.WEEKLY else 31
            )
        )

        if availabilities:
            # Calculate availability based on working hours, time-offs, existing bookings, and service duration
            availability = crud_user_availability.calculate_availability(
                availabilities=availabilities,
                time_offs=time_offs,
                bookings=bookings,
                availability_type=availability_type,
                date_from=date_from,
                service_duration_minutes=service_duration_minutes,
                company_timezone=company_timezone
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



@router.post("/companies/{company_slug}/bookings", response_model=DataResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
        *,
        db: AsyncSession = Depends(get_db),
        booking_in: BookingCreate,
        company_slug: str,
        response: Response
) -> DataResponse:
    """
    Create a new booking for both registered and unregistered customers.
    If customer is registered (token provided), use that customer.
    If not, create a new inactive customer using provided customer_info.
    """
    # Try to get customer from token if provided
    customer = None

    # Verify that the company exists
    selected_company = await crud_company.get_by_slug(db=db, slug=company_slug)
    if not selected_company:
        response.status_code = status.HTTP_404_NOT_FOUND
        raise DataResponse.error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Company not found"
        )
    booking_in.company_id = str(selected_company.id)

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
            existing_customer = await crud_customer.get(db, id=booking_in.customer_info.id)
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
            existing_customer = await crud_customer.get_by_email(db, email=str(customer_data.email))
            if existing_customer:
                customer = existing_customer
            else:
                customer = await crud_customer.create(db, obj_in=customer_data)

    # Validate booking times
    if booking_in.start_time < datetime.now(timezone.utc):
        response.status_code = status.HTTP_400_BAD_REQUEST
        raise DataResponse.error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot create booking in the past"
        )
    selected_company_users = defaultdict(list)
    for selected_company_service in booking_in.services:
        # Verify that the service exists and belongs to the company
        company_service = await crud_service.get_service(db=db, service_id=selected_company_service.category_service_id,
                                                   company_id=selected_company.id)
        if not company_service:
            response.status_code = status.HTTP_404_NOT_FOUND
            raise DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Service not found or doesn't belong to this company"
            )

        # Verify that the user(worker) exists and belongs to the company
        if selected_company_service.user_id:
            selected_user = await crud_user.get(db=db, id=selected_company_service.user_id)
            if not selected_user:
                response.status_code = status.HTTP_404_NOT_FOUND
                raise DataResponse.error_response(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="User not found or doesn't belong to this company"
                )
            selected_company_users[selected_user[0].id].append((selected_user[0], company_service))

    try:
        booking = await crud_booking.create(db=db, obj_in=booking_in, customer_id=customer.id)
        response.status_code = status.HTTP_201_CREATED
        # publish_event('booking_created', str({'info': f"A new booking has been created by {customer.first_name} {customer.last_name}"}))

        # Create confirmation notification for the assigned staff member
        booking_data = json.dumps({
            'booking_id': str(booking.id),
            'company_id': str(booking.company_id)
        }).encode('utf-8')

        _ = await notification_service.create_notification(
            db=db,
            notification_request=CompanyNotificationCreate(
                company_id=booking_in.company_id,
                type=NotificationType.BOOKING_CREATED,
                message=f"A new booking has been created by {customer.first_name} {customer.last_name}",
                data=booking_data
            )
        )

        # Get company address for calendar location
        from app.models.models import CompanyAddresses
        stmt = (select(CompanyAddresses)
                .filter(CompanyAddresses.company_id == selected_company.id))

        result = await db.execute(stmt)
        company_address = result.scalars().first()
        location = None
        if company_address:
            location = f"{company_address.address}, {company_address.city}, {company_address.country}"
            if company_address.zip:
                location = f"{company_address.address}, {company_address.city}, {company_address.zip}, {company_address.country}"

        _ = email_service.send_booking_confirmation_to_customer_email(
            to_email=customer.email,
            customer_name=customer.first_name,
            company_name=selected_company.name,
            booking_date=booking.start_at.isoformat(),
            services=[service.category_service.name for service in booking.booking_services],
            start_datetime=booking.start_at,
            end_datetime=booking.end_at,
            booking_id=booking.id,
            location=location
        )

        for user_id, item in selected_company_users.items():
            selected_service_names = []
            company_user = item[0][0]
            for user, company_service in item:
                selected_service_names.append(company_service.name)
            # Send email notification to assigned staff member
            _ = email_service.send_booking_request_to_business_email(
                to_email=company_user.email,
                staff_name=company_user.first_name,
                customer_name=booking_in.customer_info.first_name + ' ' + booking_in.customer_info.last_name,
                company_name=selected_company.name,
                booking_date=booking.start_at.isoformat(),
                services=selected_service_names,
                booking_notes=booking_in.notes,
                booking_id=booking.id
            )

        await db.commit()
        return DataResponse.success_response(
            message="Successfully created booking",
            data=None,
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        await db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to create booking: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)



@router.get("/bookings/{booking_id}", response_model=DataResponse[Booking])
async def get_booking(
        *,
        booking_id: str,
        db: AsyncSession = Depends(get_db),
        response: Response
) -> DataResponse:
    """
    Get booking by ID with details.
    """
    booking_id = UUID4(booking_id)
    booking = await crud_booking.get(db=db, id=booking_id)
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
