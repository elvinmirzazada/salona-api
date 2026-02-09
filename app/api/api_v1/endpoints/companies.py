import uuid
from typing import List
from datetime import date, timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, File, UploadFile
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
from app.models import CompanyAddresses
from app.models.models import Users, CompanyUsers
from app.models.enums import CompanyRoleType, StatusType, InvitationStatus
from app.schemas import (
    CompanyCreate, User, Company, AvailabilityResponse, AvailabilityType, CompanyUser, CompanyUserUpdate,
    CategoryServiceResponse, CompanyCategoryWithServicesResponse, Customer, TimeOff, CompanyUpdate,
    CompanyEmailCreate, CompanyEmail, CompanyEmailBase, CompanyPhoneCreate, CompanyPhone, UserCreate,
    Invitation, InvitationCreate, InvitationAccept, CompanyAddressResponse, CompanyAddressCreate, CompanyCustomer
)
from app.schemas.responses import DataResponse
from app.services.crud import company as crud_company
from app.services.crud import customer as crud_customer
from app.services.crud import service as crud_service
from app.services.crud import user_availability as crud_user_availability
from app.services.crud import booking as crud_booking
from app.services.crud import user as crud_user
from app.services.crud import user_time_off as crud_user_time_off
from app.services.crud import invitation as crud_invitation
from app.services.email_service import email_service
from app.services.auth import hash_password

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
        service_ids: List[str] = Query(None, description="List of service IDs to calculate availability based on combined service duration"),
        response: Response,
        db: Session = Depends(get_db),
        company_id: str
) -> DataResponse[AvailabilityResponse]:
    """
    Get user availability for a specific time range.
    - daily: Shows available time slots for a specific date
    - weekly: Shows available time slots for a week starting from date_from
    - monthly: Shows available time slots for the month containing date_from

    If service_ids are provided, the last available slot will be calculated based on the total duration of all services.
    """
    try:
        # Calculate total service duration if service_ids are provided
        service_duration_minutes = None
        if service_ids:
            total_duration = 0
            for service_id in service_ids:
                service = crud_service.get_service(db=db, service_id=service_id, company_id=company_id)
                if service:
                    total_duration += service.duration
            service_duration_minutes = total_duration if total_duration > 0 else None

        # Get user's regular availability
        availabilities = crud_company.get_company_user_availabilities(db, user_id=user_id, company_id=company_id)
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
            # Calculate availability based on working hours, time-offs, existing bookings, and service duration
            availability = crud_user_availability.calculate_availability(
                availabilities=availabilities,
                time_offs=time_offs,
                bookings=bookings,
                availability_type=availability_type,
                date_from=date_from,
                service_duration_minutes=service_duration_minutes
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

    return DataResponse.success_response(
        data=services,
        message="Company services retrieved successfully",
        status_code=status.HTTP_200_OK
    )


@router.get('/customers', response_model=DataResponse[List[CompanyCustomer]])
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
    customers = [Customer.model_validate(customer) for customer in customers]
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


@router.get("/{company_id}", response_model=DataResponse[Company])
async def get_company_by_id(
    *,
    db: Session = Depends(get_db),
    company_id: str
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


@router.get("/slug/{slug}", response_model=DataResponse[Company])
async def get_company_by_slug(
    *,
    db: Session = Depends(get_db),
    slug: str
) -> DataResponse:
    """
    Get a specific business by ID.
    Only the owner can access their business details.
    """
    company = crud_company.get_by_slug(db=db, slug=slug)
    if not company:
        return DataResponse.error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Company not found"
        )
    return DataResponse.success_response(
        data=company
    )

@router.get("/{company_id}/address", response_model=DataResponse[CompanyAddressResponse])
async def get_company_address(
    *,
    db: Session = Depends(get_db),
    company_id: str
) -> DataResponse:
    """
    Get the company's address by company_id.
    """
    try:
        address = db.query(CompanyAddresses).filter(
            CompanyAddresses.company_id == company_id
        ).first()

        if not address:
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Company address not found"
            )

        # Convert ORM object to Pydantic response schema
        address_response = CompanyAddressResponse.model_validate(address)

        return DataResponse.success_response(
            data=address_response,
            message="Company address retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to retrieve company address: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/address", response_model=DataResponse[CompanyAddressResponse], status_code=status.HTTP_201_CREATED)
async def create_company_address(
    *,
    db: Session = Depends(get_db),
    address_in: CompanyAddressCreate,
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)  # Only admin or owner can add address
) -> DataResponse:
    """
    Create or update a company address.
    If an address already exists for the company, it will be updated.
    Requires admin or owner role.
    """
    try:
        # Check if address already exists for this company
        existing_address = db.query(CompanyAddresses).filter(
            CompanyAddresses.company_id == company_id
        ).first()

        if existing_address:
            # Update existing address
            for field, value in address_in.model_dump(exclude_unset=True).items():
                setattr(existing_address, field, value)
            existing_address.updated_at = datetime.now()
            db.add(existing_address)
            db.commit()
            db.refresh(existing_address)
            
            return DataResponse.success_response(
                data=CompanyAddressResponse.model_validate(existing_address),
                message="Company address updated successfully",
                status_code=status.HTTP_200_OK
            )
        else:
            # Create new address
            new_address = CompanyAddresses(
                id=uuid.uuid4(),
                company_id=company_id,
                **address_in.model_dump()
            )
            db.add(new_address)
            db.commit()
            db.refresh(new_address)

            return DataResponse.success_response(
                data=CompanyAddressResponse.model_validate(new_address),
                message="Company address created successfully",
                status_code=status.HTTP_201_CREATED
            )
    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to save company address: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.patch("", response_model=DataResponse[Company])
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


@router.post("/logo", response_model=DataResponse[dict])
async def upload_company_logo(
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)  # Only admin or owner can upload logo
) -> DataResponse:
    """
    Upload company logo to S3 and update company record.
    Requires admin or owner role.
    """
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
        if file.content_type not in allowed_types:
            return DataResponse.error_response(
                message="Invalid file type. Only JPEG, PNG, and WebP are allowed",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (e.g., max 5MB)
        file_content = await file.read()
        if len(file_content) > 5 * 1024 * 1024:
            return DataResponse.error_response(
                message="File size exceeds 5MB limit",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Upload to S3
        from app.services.file_storage import file_storage_service
        logo_url = await file_storage_service.upload_file(
            file_content=file_content,
            file_name=f"companies/{company_id}/logo.{file.filename.split('.')[-1]}",
            content_type=file.content_type
        )

        # Update company record
        company = crud_company.get(db=db, id=company_id)
        if not company:
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Company not found"
            )

        _ = crud_company.update(
            db=db,
            db_obj=company,
            obj_in=CompanyUpdate(logo_url=logo_url)
        )

        return DataResponse.success_response(
            message="Company logo uploaded successfully",
            data={"logo_url": logo_url}
        )
    except Exception as e:
        return DataResponse.error_response(
            message=f"Failed to upload company logo: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/logo", response_model=DataResponse)
async def delete_company_logo(
    *,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)  # Only admin or owner can delete logo
) -> DataResponse:
    """
    Delete company logo and update company record.
    Requires admin or owner role.
    """
    try:
        # Get company
        company = crud_company.get(db=db, id=company_id)
        if not company:
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Company not found"
            )

        # Update company record to remove logo
        _ = crud_company.update(
            db=db,
            db_obj=company,
            obj_in=CompanyUpdate(logo_url=None)
        )

        return DataResponse.success_response(
            message="Company logo deleted successfully"
        )
    except Exception as e:
        return DataResponse.error_response(
            message=f"Failed to delete company logo: {str(e)}",
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


@router.get("/all/emails", response_model=DataResponse[List[CompanyEmail]])
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


@router.get("/all/phones", response_model=DataResponse[List[CompanyPhone]])
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


@router.put("/members/{user_id}", response_model=DataResponse[CompanyUser])
async def update_company_member(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    company_id: str = Depends(get_current_company_id),
    user_update: CompanyUserUpdate,
    _: None = Depends(require_admin_or_owner)  # Only admin or owner can update members
) -> DataResponse:
    """
    Update a company member's role or status.
    Requires admin or owner role.
    """
    try:
        # Validate that the update data is not empty
        update_data = user_update.model_dump(exclude_unset=True)
        if not update_data:
            return DataResponse.error_response(
                message="No fields to update",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Update the company user
        updated_company_user = crud_company.update_company_user(
            db=db,
            company_id=company_id,
            user_id=user_id,
            obj_in=user_update
        )

        if not updated_company_user:
            return DataResponse.error_response(
                message="Company user not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Get the updated company user with user details
        company_user = crud_company.get_company_user(db=db, company_id=company_id, user_id=user_id)

        return DataResponse.success_response(
            data=company_user,
            message="Company member updated successfully",
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to update company member: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/members/{user_id}", response_model=DataResponse)
async def remove_company_member(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    company_id: str = Depends(get_current_company_id),
    _: None = Depends(require_admin_or_owner)  # Only admin or owner can remove members
) -> DataResponse:
    """
    Remove a member from the company (soft delete by setting status to inactive).
    Requires admin or owner role.
    """
    try:
        # Check if the user exists in the company first
        existing_user = crud_company.get_company_user(db=db, company_id=company_id, user_id=user_id)
        if not existing_user:
            return DataResponse.error_response(
                message="Company user not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Remove the user from the company
        success = crud_company.delete_company_user(
            db=db,
            company_id=company_id,
            user_id=user_id
        )

        if not success:
            return DataResponse.error_response(
                message="Failed to remove user from company",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        return DataResponse.success_response(
            message="Company member removed successfully",
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to remove company member: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============== STAFF INVITATION ENDPOINTS ==============

@router.post("/invitations", response_model=DataResponse[Invitation], status_code=status.HTTP_201_CREATED)
async def invite_staff_member(
    *,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_current_company_id),
    invitation_in: InvitationCreate,
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_admin_or_owner)
) -> DataResponse:
    """
    Invite a staff member to the company.

    If the invited email is not registered:
    - Create invitation with PENDING status
    - Send invitation email with sign-up link

    If the invited email is already registered:
    - Create invitation with PENDING status
    - Send invitation email with acceptance link

    Requires admin or owner role.
    """
    try:
        # Check if email is already registered
        existing_user = crud_user.get_by_email(db=db, email=invitation_in.email.lower())
        is_existing_user = existing_user is not None

        # Set default role to staff if not provided
        role = invitation_in.role or CompanyRoleType.staff

        # Create invitation
        invitation = crud_invitation.create_invitation(
            db=db,
            company_id=company_id,
            email=invitation_in.email.lower(),
            role=role
        )

        # Get company details for email
        company = crud_company.get(db=db, id=company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        # Send invitation email
        invited_by = f"{current_user.first_name} {current_user.last_name}"
        email_sent = email_service.send_staff_invitation_email(
            to_email=invitation.email,
            invitation_token=invitation.token,
            invited_by=invited_by,
            company_name=company.name,
            is_existing_user=is_existing_user
        )

        if not email_sent:
            return DataResponse.error_response(
                message="Invitation created but failed to send email. Please try again.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return DataResponse.success_response(
            data=Invitation.model_validate(invitation),
            message="Staff member invited successfully",
            status_code=status.HTTP_201_CREATED
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to invite staff member: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/invitations/accept", response_model=DataResponse, status_code=status.HTTP_200_OK)
async def accept_invitation(
    *,
    db: Session = Depends(get_db),
    invitation_in: InvitationAccept,
    response: Response
) -> DataResponse:
    """
    Accept a staff invitation.

    If the user doesn't exist (new user):
    - Create user account with provided details
    - Mark invitation as USED
    - Add user to company with invited role
    - Activate company_users record

    If the user already exists (existing user):
    - Mark invitation as USED
    - Add user to company with invited role (or update if already exists)
    - Activate company_users record
    """
    try:
        # Get invitation
        invitation = crud_invitation.get_invitation_by_token(db=db, token=invitation_in.token)

        if not invitation:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                message="Invitation not found or has expired",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Check if user exists
        existing_user = crud_user.get_by_email(db=db, email=invitation.email)

        if not existing_user:
            # Create new user
            if not invitation_in.password:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return DataResponse.error_response(
                    message="Password is required for new user registration",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Hash password
            hashed_password = hash_password(invitation_in.password)

            # Create user
            user_create_data = {
                "first_name": invitation_in.first_name,
                "last_name": invitation_in.last_name,
                "email": invitation.email,
                "password": hashed_password,
                "phone": invitation_in.phone
            }

            from app.schemas.schemas import UserCreate as UserCreateSchema
            user_in = UserCreateSchema(**user_create_data)
            new_user = crud_user.create(db=db, obj_in=user_in)
            user_id = new_user.id
        else:
            # Use existing user
            user_id = existing_user.id

        # Accept invitation (mark as USED and add to company)
        crud_invitation.accept_invitation(
            db=db,
            invitation=invitation,
            user_id=user_id
        )

        return DataResponse.success_response(
            message="Invitation accepted successfully",
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to accept invitation: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/invitations/{token}/resend", response_model=DataResponse[Invitation])
async def resend_invitation(
    *,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_current_company_id),
    token: str,
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_admin_or_owner)
) -> DataResponse:
    """
    Resend an invitation to a staff member.

    This generates a new token and resets the invitation to PENDING status.
    Only works for expired or pending invitations.

    Requires admin or owner role.
    """
    try:
        from app.models.models import Invitations

        # Get the invitation by current token
        invitation = db.query(Invitations).filter(
            Invitations.token == token,
            Invitations.company_id == company_id
        ).first()

        if not invitation:
            return DataResponse.error_response(
                message="Invitation not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Resend invitation
        resent_invitation = crud_invitation.resend_invitation(
            db=db,
            company_id=company_id,
            email=invitation.email
        )

        if not resent_invitation:
            return DataResponse.error_response(
                message="Invitation not found or cannot be resent",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Get company details for email
        company = crud_company.get(db=db, id=company_id)

        # Check if user exists for email
        existing_user = crud_user.get_by_email(db=db, email=resent_invitation.email)
        is_existing_user = existing_user is not None

        # Send invitation email
        invited_by = f"{current_user.first_name} {current_user.last_name}"
        email_sent = email_service.send_staff_invitation_email(
            to_email=resent_invitation.email,
            invitation_token=resent_invitation.token,
            invited_by=invited_by,
            company_name=company.name,
            is_existing_user=is_existing_user
        )

        if not email_sent:
            return DataResponse.error_response(
                message="Invitation updated but failed to send email",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return DataResponse.success_response(
            data=Invitation.model_validate(resent_invitation),
            message="Invitation resent successfully",
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to resend invitation: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/all/invitations", response_model=DataResponse[List[Invitation]])
async def get_company_invitations(
    *,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_current_company_id),
    status_filter: str = Query(None, description="Filter by status: pending, used, expired, declined"),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_admin_or_owner)
) -> DataResponse:
    """
    Get all invitations for a company.

    Optional status filter: pending, used, expired, declined

    Requires admin or owner role.
    """
    try:
        from app.models.enums import InvitationStatus

        # Parse status filter
        status_enum = None
        if status_filter:
            status_enum = InvitationStatus(status_filter.upper())

        invitations = crud_invitation.get_company_invitations(
            db=db,
            company_id=company_id,
            status=status_enum
        )

        return DataResponse.success_response(
            data=[Invitation.model_validate(inv) for inv in invitations],
            message="Company invitations retrieved successfully",
            status_code=status.HTTP_200_OK
        )

    except ValueError:
        return DataResponse.error_response(
            message="Invalid status filter",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return DataResponse.error_response(
            message=f"Failed to retrieve invitations: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/invitations/{token}/check-and-join", response_model=DataResponse, status_code=status.HTTP_200_OK)
async def check_invitation_and_join(
    *,
    db: Session = Depends(get_db),
    token: str,
    response: Response
) -> DataResponse:
    """
    Check if the email from invitation is registered.
    If registered, add user to company and return status.
    If not registered, return different status so UI knows to show signup form.

    Returns:
    - status: "user_exists" - User is registered, added to company, ready to accept
    - status: "user_not_found" - User not registered, show signup form
    - status: "invitation_expired" - Invitation has expired
    - status: "already_member" - User already a member of this company
    """
    try:
        # Get invitation by token
        invitation = crud_invitation.get_invitation_by_token(db=db, token=token)

        if not invitation:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                message="Invitation not found or has expired",
                status_code=status.HTTP_404_NOT_FOUND,
                data={"status": "invitation_expired"}
            )

        # Check if user exists with this email
        existing_user = crud_user.get_by_email(db=db, email=invitation.email)

        if not existing_user:
            # User doesn't exist - return status for UI to show signup form
            return DataResponse.success_response(
                message="Email not registered. Please sign up.",
                status_code=status.HTTP_200_OK,
                data={
                    "status": "user_not_found",
                    "email": invitation.email,
                    "company_id": str(invitation.company_id),
                    "role": invitation.role,
                    "token": token
                }
            )

        # Check if user is already a member of this company
        existing_company_user = db.query(CompanyUsers).filter(
            CompanyUsers.user_id == existing_user.id,
            CompanyUsers.company_id == invitation.company_id
        ).first()

        if existing_company_user:
            # User already a member
            if existing_company_user.status == StatusType.active:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return DataResponse.error_response(
                    message="User is already a member of this company",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    data={"status": "already_member"}
                )
            else:
                # Update status to active and role based on invitation
                existing_company_user.status = StatusType.active
                existing_company_user.role = invitation.role
                db.add(existing_company_user)

                # Mark invitation as used
                invitation.status = InvitationStatus.USED
                invitation.updated_at = datetime.now()
                db.add(invitation)
                db.commit()

                return DataResponse.success_response(
                    message="User successfully joined the company",
                    status_code=status.HTTP_200_OK,
                    data={
                        "status": "user_exists",
                        "user_id": str(existing_user.id),
                        "email": existing_user.email,
                        "first_name": existing_user.first_name,
                        "last_name": existing_user.last_name,
                        "company_id": str(invitation.company_id),
                        "role": invitation.role,
                        "message": "Rejoined the company"
                    }
                )

        # User exists but not yet a member - add them to company
        company_user = CompanyUsers(
            id=uuid.uuid4(),
            user_id=existing_user.id,
            company_id=invitation.company_id,
            role=invitation.role,
            status=StatusType.active
        )
        db.add(company_user)

        # Mark invitation as used
        # invitation.status = InvitationStatus.USED
        invitation.updated_at = datetime.now()
        db.add(invitation)
        db.commit()

        # User exists and has been added to company
        return DataResponse.success_response(
            message="Registered user added to company successfully",
            status_code=status.HTTP_200_OK,
            data={
                "status": "user_exists",
                "user_id": str(existing_user.id),
                "email": existing_user.email,
                "first_name": existing_user.first_name,
                "last_name": existing_user.last_name,
                "company_id": str(invitation.company_id),
                "role": invitation.role,
                "message": "User joined the company"
            }
        )

    except Exception as e:
        db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to process invitation: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
