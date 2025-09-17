from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic.v1 import UUID4
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import Booking, BookingCreate, BookingUpdate
from app.services.crud import service as crud_service, company as crud_company, user as crud_user, booking as crud_booking
from app.schemas.schemas import User
from app.api.dependencies import get_current_active_customer

router = APIRouter()


@router.post("", response_model=Booking, status_code=status.HTTP_201_CREATED)
def create_booking(
    *,
    db: Session = Depends(get_db),
    booking_in: BookingCreate,
    current_customer: User = Depends(get_current_active_customer)
) -> Booking:
    """
    Create a new booking.
    """
    # Verify that the company exists
    selected_company = crud_company.get(db=db, id=booking_in.company_id)
    if not selected_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected company not found"
        )


    for selected_company_service in booking_in.services:

        # Verify that the service exists and belongs to the company
        company_service = crud_service.get_company_service(db=db, id=selected_company_service.company_service_id)
        if not company_service or company_service.company_id != booking_in.company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found or doesn't belong to this company"
            )

        # # Verify that the user(worker) exists and belongs to the company
        selected_user = crud_user.get(db=db, id=selected_company_service.user_id)
        if not selected_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or doesn't belong to this company"
            )

    # Validate booking times
    if booking_in.start_time < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create booking in the past"
        )

    booking = crud_booking.create(db=db, obj_in=booking_in, customer_id=current_customer.id)
    return booking


@router.get("/{booking_id}", response_model=Booking)
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_customer: User = Depends(get_current_active_customer)
) -> Booking:
    """
    Get booking by ID with details.
    """
    booking_id = UUID4(booking_id)
    booking = crud_booking.get(db=db, id=booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    return booking


@router.get("", response_model=List[Booking])
def get_all_bookings(
    db: Session = Depends(get_db),
    current_customer: User = Depends(get_current_active_customer)
) -> List[Booking]:
    """
    Get booking by ID with details.
    """
    bookings = crud_booking.get_all(db=db)
    if not bookings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    return bookings
#
#
# @router.get("/business/{business_id}", response_model=List[Appointment])
# def get_appointments_by_business(
#     business_id: int,
#     skip: int = 0,
#     limit: int = 100,
#     db: Session = Depends(get_db)
# ) -> List[Appointment]:
#     """
#     Get all appointments for a business.
#     """
#     appointments = crud_appointment.get_multi_by_business(db=db, business_id=business_id, skip=skip, limit=limit)
#     return appointments
#
#
# @router.get("/client/{client_id}", response_model=List[Appointment])
# def get_appointments_by_client(
#     client_id: int,
#     skip: int = 0,
#     limit: int = 100,
#     db: Session = Depends(get_db)
# ) -> List[Appointment]:
#     """
#     Get all appointments for a client.
#     """
#     appointments = crud_appointment.get_multi_by_client(db=db, client_id=client_id, skip=skip, limit=limit)
#     return appointments
#
#
# @router.put("/{appointment_id}", response_model=Appointment)
# def update_appointment(
#     *,
#     db: Session = Depends(get_db),
#     appointment_id: int,
#     appointment_in: AppointmentUpdate
# ) -> Appointment:
#     """
#     Update appointment.
#     """
#     appointment = crud_appointment.get(db=db, id=appointment_id)
#     if not appointment:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Appointment not found"
#         )
#
#     # If updating times, validate them
#     if appointment_in.start_time and appointment_in.end_time:
#         if appointment_in.start_time >= appointment_in.end_time:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Start time must be before end time"
#             )
#
#     appointment = crud_appointment.update(db=db, db_obj=appointment, obj_in=appointment_in)
#     return appointment
