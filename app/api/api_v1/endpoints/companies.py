from typing import List
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from app.api.dependencies import (
    get_current_active_user,
    get_current_active_customer,
    get_current_company_id,
    require_admin_or_owner,
    require_owner,
    require_staff_or_higher,
    get_current_user_role
)
from app.db.session import get_db
from app.models.models import Users
from app.models.enums import CompanyRoleType
from app.schemas import CompanyCreate, User, Company, AvailabilityResponse, AvailabilityType, CompanyUser, \
    CategoryServiceResponse, CompanyCategoryWithServicesResponse, Customer, TimeOff, CompanyUpdate, \
    CompanyEmailCreate, CompanyEmail, CompanyEmailBase, CompanyPhoneCreate, CompanyPhone, UserCreate
from app.schemas.responses import DataResponse
from app.services.crud import company as crud_company
from app.services.crud import customer as crud_customer
from app.services.crud import service as crud_service
from app.services.crud import user_availability as crud_user_availability
from app.services.crud import booking as crud_booking
from app.services.crud import user as crud_user
from app.services.crud import user_time_off as crud_user_time_off

router = APIRouter()


@router.post("", response_model=DataResponse[Company], status_code=status.HTTP_201_CREATED)
async def create_company(
    *,
    db: Session = Depends(get_db),
    company_in: CompanyCreate,
    current_user: User = Depends(get_current_active_user)
) -> DataResponse:
    """
    Create a new company.
    """
    company = crud_company.create(db=db, obj_in=company_in, current_user=current_user)
    return DataResponse.success_response(
        data=company,
        message="Company created successfully",
        status_code=status.HTTP_201_CREATED
    )


@router.get("/{company_id}/users/{user_id}/availability", response_model=DataResponse[AvailabilityResponse])
async def get_user_availability(
        *,
        user_id: str,
        availability_type: AvailabilityType = Query(..., description="Type of availability check: daily, weekly, or monthly"),
        date_from: date = Query(..., description="Start date for availability check"),
        response: Response,
        db: Session = Depends(get_db),
        company_id: str
) -> DataResponse[AvailabilityResponse]:
    """
    Get user availability for a specific time range.
    - daily: Shows available time slots for a specific date
    - weekly: Shows available time slots for a week starting from date_from
    - monthly: Shows available time slots for the month containing date_from
    """
    try:
        # Get user's regular availability
        availabilities = crud_company.get_company_user_availabilities(db, user_id=user_id, company_id=company_id)
        if not availabilities:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                message="No availability schedule found for this user",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Get user's time-offs
        time_offs = crud_company.get_company_user_time_offs(
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
            availability = crud_user_availability.calculate_availability(
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


@router.get("/{company_id}/availabilities", response_model=DataResponse[list[AvailabilityResponse]])
async def get_company_all_users_availabilities(
        *,
        availability_type: AvailabilityType = Query(..., description="Type of availability check: daily, weekly, or monthly"),
        date_from: date = Query(..., description="Start date for availability check"),
        response: Response,
        db: Session = Depends(get_db),
        company_id: str
) -> DataResponse[list[AvailabilityResponse]]:
    """
    Get availabilities for all users for a specific time range. Optimized to fetch all data in bulk and group bookings by user via BookingServices.
    """
    try:
        company_users = crud_company.get_company_users(db, company_id)
        if not company_users:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                message="No users found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        # Bulk fetch all related data
        availabilities = crud_company.get_company_all_users_availabilities(db, company_id)
        time_offs = crud_company.get_company_all_users_time_offs(
            db,
            company_id=company_id,
            start_date=date_from,
            end_date=date_from + timedelta(
                days=1 if availability_type == AvailabilityType.DAILY else
                     7 if availability_type == AvailabilityType.WEEKLY else 31
            )
        )
        booking_tuples = crud_booking.get_all_bookings_in_range(
            db,
            start_date=date_from,
            end_date=date_from + timedelta(
                days=1 if availability_type == AvailabilityType.DAILY else
                     7 if availability_type == AvailabilityType.WEEKLY else 31
            )
        )
        # Group data by user
        avail_map = {}
        for a in availabilities:
            avail_map.setdefault(str(a.user_id), []).append(a)
        timeoff_map = {}
        for t in time_offs:
            timeoff_map.setdefault(str(t.user_id), []).append(t)
        booking_map = {}
        for booking, user_id in booking_tuples:
            booking_map.setdefault(str(user_id), []).append(booking)
        results = []
        for user in company_users:
            user_id = str(user.user_id)
            user_avails = avail_map.get(user_id, [])
            if not user_avails:
                continue
            user_timeoffs = timeoff_map.get(user_id, [])
            user_bookings = booking_map.get(user_id, [])
            availability = crud_user_availability.calculate_availability(
                availabilities=user_avails,
                time_offs=user_timeoffs,
                bookings=user_bookings,
                availability_type=availability_type,
                date_from=date_from
            )
            results.append(availability)
        if not results:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                message="No availabilities found for any user",
                status_code=status.HTTP_404_NOT_FOUND
            )
        return DataResponse.success_response(
            data=results,
            message="Availabilities retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to retrieve availabilities: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/users", response_model=DataResponse[List[CompanyUser]])
async def get_company_users(
        db: Session = Depends(get_db),
        company_id: str = Depends(get_current_company_id),
        user_role: CompanyRoleType = Depends(require_admin_or_owner)  # Only admin or owner can list staff
) -> DataResponse:
    """
    Get all staff/users in the company.
    Requires admin or owner role.
    """
    if not company_id:
        return DataResponse.error_response(
            message="No company associated with the current user",
            status_code=status.HTTP_404_NOT_FOUND
        )
    users = crud_company.get_company_users(
        db=db, company_id=company_id
    )
    return DataResponse.success_response(
        data=users,
        message="Company users retrieved successfully",
        status_code=status.HTTP_200_OK
    )


@router.get("/services", response_model=DataResponse[List[CompanyCategoryWithServicesResponse]])
async def get_company_services(
        db: Session = Depends(get_db),
        company_id: str = Depends(get_current_company_id),
) -> DataResponse:
    """
    Get all businesses owned by the authenticated professional.
    """
    services = crud_service.get_company_services(
        db=db, company_id=company_id
    )
    from app.core.redis_client import publish_event
    await publish_event('booking_created',
                        str({'info': f"A new booking has been created"}))

    return DataResponse.success_response(
        data=services,
        message="Company services retrieved successfully",
        status_code=status.HTTP_200_OK
    )


@router.get('/customers', response_model=DataResponse[List[Customer]])
async def get_company_customers(
        db: Session = Depends(get_db),
        company_id: str = Depends(get_current_company_id),
        user_role: CompanyRoleType = Depends(require_staff_or_higher)  # Staff and above can view customers
) -> DataResponse:
    """
    Get all customers who have bookings with the company.
    Requires staff, admin, or owner role.
    """
    customers = crud_customer.get_company_customers(
        db=db, company_id=company_id
    )

    return DataResponse.success_response(
        data=customers,
        message="Company customers retrieved successfully",
        status_code=status.HTTP_200_OK
    )


@router.get('/user-time-offs', response_model=DataResponse[List[TimeOff]])
async def get_company_user_time_offs(
        db: Session = Depends(get_db),
        company_id: str = Depends(get_current_company_id),
        availability_type: AvailabilityType = Query(..., description="Type of availability check: daily, weekly, or monthly"),
        date_from: date = Query(..., description="Start date for availability check"),
        user_role: CompanyRoleType = Depends(require_staff_or_higher)
) -> DataResponse:
    """
    Get all user time offs for the company.
    Requires admin or owner role.
    """
    start_date = date_from
    end_date = date_from + timedelta(
        days=1 if availability_type == AvailabilityType.DAILY else
        7 if availability_type == AvailabilityType.WEEKLY else 31
    )
    time_offs = crud_user_time_off.get_company_user_time_offs(
        db=db, company_id=company_id, start_date=start_date, end_date=end_date
    )

    return DataResponse.success_response(
        data=time_offs,
        message="Company user time offs retrieved successfully",
        status_code=status.HTTP_200_OK
    )


@router.get("", response_model=DataResponse[Company])
async def get_company(
    *,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Get a specific business by ID.
    Only the owner can access their business details.
    """
    company = crud_company.get(db=db, id=company_id)
    if not company:
        return DataResponse.error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Company not found"
        )
    return DataResponse.success_response(
        data=company
    )


@router.put("", response_model=DataResponse[Company])
async def update_company(
    *,
    db: Session = Depends(get_db),
    company_in: CompanyUpdate,
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)  # Only admin or owner can update company
) -> DataResponse:
    """
    Update company information.
    Requires admin or owner role.
    """
    company = crud_company.get(db=db, id=company_id)
    if not company:
        return DataResponse.error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Company not found"
        )

    try:
        updated_company = crud_company.update(
            db=db,
            db_obj=company,
            obj_in=company_in.model_dump(exclude_unset=True)
        )
        return DataResponse.success_response(
            data=updated_company,
            message="Company information updated successfully"
        )
    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to update company information: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/emails", response_model=DataResponse, status_code=status.HTTP_201_CREATED)
async def add_company_email(
    *,
    db: Session = Depends(get_db),
    email_in: CompanyEmailCreate,
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)  # Only admin or owner
) -> DataResponse:
    """
    Add a new email address to the company.
    Requires admin or owner role.
    """
    try:
        email_in.company_id = company_id
        crud_company.create_company_email(db=db, obj_in=email_in)

        return DataResponse.success_response(
            message="Emails added successfully",
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to add emails: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/emails", response_model=DataResponse[List[CompanyEmail]])
async def get_company_emails(
    *,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Get all email addresses associated with the company.
    """
    emails = crud_company.get_company_emails(db=db, company_id=company_id)

    return DataResponse.success_response(
        data=emails,
        message="Company emails retrieved successfully",
        status_code=status.HTTP_200_OK
    )


@router.delete("/emails/{email_id}", response_model=DataResponse)
async def delete_company_email(
    *,
    db: Session = Depends(get_db),
    email_id: str,
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)  # Only admin or owner
) -> DataResponse:
    """
    Delete an email address from the company.
    Requires admin or owner role.
    """
    success = crud_company.delete_company_email(db=db, email_id=email_id, company_id=company_id)

    if not success:
        return DataResponse.error_response(
            message="Email not found or does not belong to this company",
            status_code=status.HTTP_404_NOT_FOUND
        )

    return DataResponse.success_response(
        message="Email deleted successfully",
        status_code=status.HTTP_200_OK
    )


@router.post("/phones", response_model=DataResponse[List[CompanyPhone]], status_code=status.HTTP_201_CREATED)
async def add_company_phone(
    *,
    db: Session = Depends(get_db),
    phone_in: CompanyPhoneCreate,
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)  # Only admin or owner
) -> DataResponse:
    """
    Add new phone numbers to the company.
    Requires admin or owner role.
    """
    try:
        # Set the company ID from the authenticated user's context
        phone_in.company_id = company_id
        phones = crud_company.create_company_phone(db=db, obj_in=phone_in)

        return DataResponse.success_response(
            data=phones,
            message="Phone numbers added successfully",
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to add phone numbers: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/phones", response_model=DataResponse[List[CompanyPhone]])
async def get_company_phones(
    *,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Get all phone numbers associated with the company.
    """
    phones = crud_company.get_company_phones(db=db, company_id=company_id)

    return DataResponse.success_response(
        data=phones,
        message="Company phone numbers retrieved successfully",
        status_code=status.HTTP_200_OK
    )


@router.delete("/phones/{phone_id}", response_model=DataResponse)
async def delete_company_phone(
    *,
    db: Session = Depends(get_db),
    phone_id: str,
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)  # Only admin or owner
) -> DataResponse:
    """
    Delete a phone number from the company.
    Requires admin or owner role.
    """
    success = crud_company.delete_company_phone(db=db, phone_id=phone_id, company_id=company_id)

    if not success:
        return DataResponse.error_response(
            message="Phone number not found or does not belong to this company",
            status_code=status.HTTP_404_NOT_FOUND
        )

    return DataResponse.success_response(
        message="Phone number deleted successfully",
        status_code=status.HTTP_200_OK
    )
@router.post("/members", response_model=DataResponse[CompanyUser], status_code=status.HTTP_201_CREATED)
async def add_company_member(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    role: CompanyRoleType = Query(..., description="Role to assign to the user in the company"),
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)  # Only admin or owner can add members
) -> DataResponse:
    """
    Create a new user and add them to the company with a specified role.
    If a user with the email already exists, they will be added to the company.
    Requires admin or owner role.
    """
    try:
        company_user = crud_company.create_company_member(
            db=db,
            user_in=user_in,
            company_id=company_id,
            role=role
        )
        return DataResponse.success_response(
            data=company_user,
            message="Member added to company successfully",
            status_code=status.HTTP_201_CREATED
        )
    except ValueError as e:
        return DataResponse.error_response(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to add member to company: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@router.post("/members", response_model=DataResponse[CompanyUser], status_code=status.HTTP_201_CREATED)
async def add_company_member(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    role: CompanyRoleType = Query(..., description="Role to assign to the user in the company"),
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)  # Only admin or owner can add members
) -> DataResponse:
    """
    Create a new user and add them to the company with a specified role.
    If a user with the email already exists, they will be added to the company.
    Requires admin or owner role.
    """
    try:
        company_user = crud_company.create_company_member(
            db=db,
            user_in=user_in,
            company_id=company_id,
            role=role
        )
        return DataResponse.success_response(
            data=company_user,
            message="Member added to company successfully",
            status_code=status.HTTP_201_CREATED
        )
    except ValueError as e:
        return DataResponse.error_response(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to add member to company: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
