from typing import List
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user, get_current_active_customer, get_current_company_id
from app.db.session import get_db
from app.models.models import Users
from app.schemas import CompanyCreate, User, Company, AvailabilityResponse, AvailabilityType
from app.schemas.responses import DataResponse
from app.services.crud import company as crud_company
from app.services.crud import user_availability as crud_user_availability
from app.services.crud import booking as crud_booking
from app.services.crud import user as crud_user

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


@router.get("/users/{user_id}/availability", response_model=DataResponse[AvailabilityResponse])
async def get_user_availability(
        *,
        user_id: str,
        availability_type: AvailabilityType = Query(..., description="Type of availability check: daily, weekly, or monthly"),
        date_from: date = Query(..., description="Start date for availability check"),
        response: Response,
        db: Session = Depends(get_db),
        company_id: str = Depends(get_current_company_id)
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


@router.get("/availabilities", response_model=DataResponse[list[AvailabilityResponse]])
async def get_company_all_users_availabilities(
        *,
        availability_type: AvailabilityType = Query(..., description="Type of availability check: daily, weekly, or monthly"),
        date_from: date = Query(..., description="Start date for availability check"),
        response: Response,
        db: Session = Depends(get_db),
        company_id: str = Depends(get_current_company_id)
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


#
# @router.post("/add-member", response_model=BusinessStaff, status_code=status.HTTP_201_CREATED)
# async def add_business_member(
#     *,
#     db: Session = Depends(get_db),
#     business_staff_in: BusinessStaffCreate,
#     current_professional: Professional = Depends(get_current_active_professional)
# ) -> BusinessStaff:
#     """
#     Add a new member to the business.
#     """
#     business = crud_business.business.get(db=db, id=business_staff_in.business_id)
#     if not business:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Business not found"
#         )
#     if business.owner_id != current_professional.id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not enough permissions to add members to this business"
#         )
#     business_staff_in.professional_id = current_professional.id
#     business_staff = crud_business.business_staff.create(db=db, obj_in=business_staff_in)
#     return business_staff
#
#
# @router.get("/my-businesses", response_model=List[BusinessWithDetails])
# async def get_my_businesses(
#     db: Session = Depends(get_db),
#     current_professional: Professional = Depends(get_current_active_professional),
#     skip: int = 0,
#     limit: int = 10,
# ) -> List[Business]:
#     """
#     Get all businesses owned by the authenticated professional.
#     """
#     businesses = crud_business.business.get_multi_by_owner(
#         db=db,
#         owner_id=current_professional.id,
#         skip=skip,
#         limit=limit
#     )
#     return businesses
#
#
# @router.get("/{business_id}", response_model=BusinessWithDetails)
# async def get_business(
#     *,
#     db: Session = Depends(get_db),
#     business_id: int,
#     current_professional: Professional = Depends(get_current_active_professional)
# ) -> Business:
#     """
#     Get a specific business by ID.
#     Only the owner can access their business details.
#     """
#     business = crud_business.business.get(db=db, id=business_id)
#     if not business:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Business not found"
#         )
#     if business.owner_id != current_professional.id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not enough permissions to access this business"
#         )
#     return business
