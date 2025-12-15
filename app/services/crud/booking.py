from datetime import timedelta, timezone
from typing import List, Optional, Any
from datetime import date, datetime

from pydantic.v1 import UUID4
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import BookingServices, Customers
from app.models.models import Bookings
from app.models.enums import BookingStatus
from app.schemas import BookingServiceRequest
from app.schemas.schemas import BookingCreate, BookingUpdate
from app.services.crud import service
from app.core.redis_client import publish_event
from app.services.crud.company import get_company_users
from app.core.datetime_utils import utcnow, ensure_utc


def get(db: Session, id: UUID4) -> Optional[Bookings]:
    return db.query(Bookings).filter(Bookings.id == id).first()


def get_all(db: Session, skip: int = 0, limit: int = 100) -> list[type[Bookings]]:
    return list(db.query(Bookings).offset(skip).limit(limit).all())

def get_user_bookings_in_range(db: Session, user_id: str, start_date: Any, end_date: Any) -> list["Bookings"]:
    return list(db.query(Bookings).join(BookingServices).filter(
        BookingServices.user_id == user_id,
        Bookings.start_at >= start_date,
        Bookings.end_at <= end_date
    ).all())

def get_all_bookings_in_range(db: Session, start_date: date, end_date: date):
    # Join Bookings and BookingServices, return tuples of (booking, user_id)
    return db.query(Bookings, BookingServices.user_id).join(BookingServices, Bookings.id == BookingServices.booking_id).filter(
        Bookings.start_at >= start_date,
        Bookings.end_at <= end_date
    ).all()


def get_all_bookings_in_range_by_company(db: Session, company_id: str, start_date: date, end_date: date):
    # Convert dates to UTC datetime if they aren't already
    start_datetime = ensure_utc(datetime.combine(start_date, datetime.min.time()))
    end_datetime = ensure_utc(datetime.combine(end_date, datetime.max.time()))

    return db.query(Bookings).join(BookingServices, Bookings.id == BookingServices.booking_id).filter(
        Bookings.company_id == company_id,
        Bookings.start_at >= start_datetime,
        Bookings.end_at <= end_datetime,
        Bookings.status.in_(['scheduled', 'confirmed', 'completed'])
    ).all()


def check_staff_availability(db: Session, user_id: UUID4, start_time: datetime, end_time: datetime, exclude_booking_id: Optional[UUID4] = None) -> tuple[bool, Optional[str]]:
    """
    Check if a staff member is available during the requested time period.
    
    Args:
        db: Database session
        user_id: The staff member's user ID
        start_time: Start time of the requested booking
        end_time: End time of the requested booking
        exclude_booking_id: Optional booking ID to exclude from the check (for updates)
    
    Returns:
        Tuple of (is_available: bool, conflict_message: Optional[str])
    """
    # Query for overlapping bookings for this staff member
    query = db.query(BookingServices).join(Bookings).filter(
        BookingServices.user_id == user_id,
        Bookings.status.in_([BookingStatus.SCHEDULED, BookingStatus.CONFIRMED]),
        # Check for time overlap: (start_time < existing_end AND end_time > existing_start)
        BookingServices.start_at < end_time,
        BookingServices.end_at > start_time
    )
    
    # Exclude the current booking if updating
    if exclude_booking_id:
        query = query.filter(Bookings.id != exclude_booking_id)
    
    conflicting_bookings = query.all()
    
    if conflicting_bookings:
        conflict = conflicting_bookings[0]
        conflict_message = f"Staff member is not available. There is a conflicting booking from {conflict.start_at.strftime('%H:%M')} to {conflict.end_at.strftime('%H:%M')}"
        return False, conflict_message
    
    return True, None


def calc_service_params(db, services: List[BookingServiceRequest], company_id: str = None) -> tuple[int, int]:
    total_duration = 0
    total_price = 0

    for srv in services:
        selected_srv = service.get_service(db, srv.category_service_id, company_id)
        total_duration += selected_srv.duration
        total_price += int(selected_srv.discount_price or selected_srv.price)

    return total_duration, total_price


def create(db: Session, *, obj_in: BookingCreate, customer_id: UUID4) -> Bookings:
    total_duration, total_price = calc_service_params(db, obj_in.services, obj_in.company_id)

    # Ensure start_time is in UTC
    start_time_utc = ensure_utc(obj_in.start_time)
    end_time_utc = start_time_utc + timedelta(minutes=total_duration)

    db_obj = Bookings(
        customer_id=customer_id,
        company_id=obj_in.company_id,
        start_at=start_time_utc,
        end_at=end_time_utc,
        total_price=total_price,
        notes=obj_in.notes
    )
    db.add(db_obj)
    db.commit()

    current_start_time = start_time_utc
    for srv in obj_in.services:
        if not srv.user_id:
            srv.user_id = get_company_users(db, str(obj_in.company_id))[0].user_id
        duration, _ = calc_service_params(db, [srv], obj_in.company_id)
        service_end_time = current_start_time + timedelta(minutes=duration)

        db_service_obj = BookingServices(
            booking_id=db_obj.id,
            category_service_id=srv.category_service_id,
            user_id=srv.user_id,
            notes=srv.notes,
            start_at=current_start_time,
            end_at=service_end_time
        )
        current_start_time = service_end_time
        db.add(db_service_obj)

    db.commit()
    db.refresh(db_obj)
    # Publish booking created event
    # publish_event("booking_created", str(db_obj.id))
    return db_obj


def update(db: Session, *, db_obj: Bookings, obj_in: BookingUpdate) -> Bookings:
    """
    Update a booking and its associated services.
    """
    # Update basic booking fields
    if obj_in.notes is not None:
        db_obj.notes = obj_in.notes
    if obj_in.status is not None:
        db_obj.status = obj_in.status

    # If services are being updated, we need to recalculate everything
    if obj_in.services is not None:
        # Update start time if provided
        if obj_in.start_time is not None:
            db_obj.start_at = ensure_utc(obj_in.start_time)

        # Remove existing booking services
        db.query(BookingServices).filter(BookingServices.booking_id == db_obj.id).delete()

        # Recalculate total duration and price
        total_duration, total_price = calc_service_params(db, obj_in.services, str(db_obj.company_id))
        db_obj.total_price = total_price

        # Update end time based on new start time and duration
        start_time = db_obj.start_at
        db_obj.end_at = start_time + timedelta(minutes=total_duration)

        # Create new booking services
        current_start_time = start_time
        for srv in obj_in.services:
            duration, _ = calc_service_params(db, [srv], str(db_obj.company_id))
            db_service_obj = BookingServices(
                booking_id=db_obj.id,
                category_service_id=srv.category_service_id,
                user_id=srv.user_id,
                notes=srv.notes,
                start_at=current_start_time,
                end_at=current_start_time + timedelta(minutes=duration)
            )
            current_start_time = ensure_utc(db_service_obj.end_at)
            db.add(db_service_obj)

    # If only start_time is being updated (without services)
    elif obj_in.start_time is not None:
        # Get existing booking services
        existing_services = db.query(BookingServices).filter(
            BookingServices.booking_id == db_obj.id
        ).order_by(BookingServices.start_at).all()

        # Ensure timezone awareness before calculating time difference
        new_start_time = ensure_utc(obj_in.start_time)
        old_start_time = ensure_utc(db_obj.start_at)

        # Calculate the time difference
        time_diff = new_start_time - old_start_time

        # Update booking start and end times
        db_obj.start_at = new_start_time
        db_obj.end_at = ensure_utc(db_obj.end_at) + time_diff

        # Update all existing booking services with the new times
        current_start_time = new_start_time
        for booking_service in existing_services:
            # Ensure timezone awareness for service times
            service_start = ensure_utc(booking_service.start_at)
            service_end = ensure_utc(booking_service.end_at)

            # Calculate the duration of this service
            service_duration = service_end - service_start

            # Update the service times
            booking_service.start_at = current_start_time
            booking_service.end_at = current_start_time + service_duration

            current_start_time = booking_service.end_at
            db.add(booking_service)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def cancel(db: Session, *, booking_id: UUID4) -> Optional[Bookings]:
    """
    Cancel a booking by setting its status to CANCELLED.
    Returns the updated booking or None if booking not found.
    """
    db_obj = db.query(Bookings).filter(Bookings.id == booking_id).first()
    if db_obj:
        db_obj.status = BookingStatus.CANCELLED
        db.add(db_obj)
        db.flush()  # Flush to get the updated object but don't commit yet
        return db_obj
    return None


def confirm(db: Session, *, booking_id: UUID4) -> Optional[Bookings]:
    """
    Confirm a booking by setting its status to CONFIRMED.
    Returns the updated booking or None if booking not found.
    """
    db_obj = db.query(Bookings).filter(Bookings.id == booking_id).first()
    if db_obj:
        db_obj.status = BookingStatus.CONFIRMED
        db.add(db_obj)
        db.flush()  # Flush to get the updated object but don't commit yet
        return db_obj
    return None


def complete(db: Session, *, booking_id: UUID4) -> Optional[Bookings]:
    """
    Complete a booking by setting its status to COMPLETED.
    Returns the updated booking or None if booking not found.
    """
    db_obj = db.query(Bookings).filter(Bookings.id == booking_id).first()
    if db_obj:
        db_obj.status = BookingStatus.COMPLETED
        db.add(db_obj)
        db.flush()  # Flush to get the updated object but don't commit yet
        return db_obj
    return None
