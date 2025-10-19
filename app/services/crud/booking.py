from datetime import timedelta
from typing import List, Optional, Any
from datetime import date

from pydantic.v1 import UUID4
from sqlalchemy.orm import Session

from app.models import BookingServices, Customers
from app.models.models import Bookings
from app.models.enums import BookingStatus
from app.schemas import BookingServiceRequest
from app.schemas.schemas import BookingCreate, BookingUpdate
from app.services.crud import service
from app.core.redis_client import publish_event


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
    return (db.query(Bookings).join(BookingServices, Bookings.id == BookingServices.booking_id)
          .filter(
        Bookings.company_id == company_id,
        Bookings.start_at >= start_date,
        Bookings.end_at <= end_date,
        Bookings.status.in_(['scheduled', 'confirmed', 'completed'])
    ).all())

def calc_service_params(db, services: List[BookingServiceRequest], company_id: str = None) -> tuple[int, int]:
    total_duration = 0
    total_price = 0

    for srv in services:
        selected_srv = service.get_service(db, srv.category_service_id, company_id)
        total_duration += selected_srv.duration
        total_price += int(selected_srv.price)

    return total_duration, total_price


def create(db: Session, *, obj_in: BookingCreate, customer_id: UUID4) -> Bookings:
    total_duration, total_price = calc_service_params(db, obj_in.services, obj_in.company_id)
    db_obj = Bookings(
        customer_id=customer_id,
        company_id=obj_in.company_id,
        start_at=obj_in.start_time,
        end_at= obj_in.start_time + timedelta(minutes=total_duration),
        total_price=total_price,
        notes=obj_in.notes
    )
    db.add(db_obj)
    db.commit()

    start_time = obj_in.start_time
    for srv in obj_in.services:
        duration, _ = calc_service_params(db, [srv], obj_in.company_id)
        db_service_obj = BookingServices(
            booking_id=db_obj.id,
            category_service_id=srv.category_service_id,
            user_id=srv.user_id,
            notes=srv.notes,
            start_at=start_time,
            end_at=start_time + timedelta(minutes=duration)
        )
        start_time = db_service_obj.end_at
        db.add(db_service_obj)

    db.commit()
    db.refresh(db_obj)
    # Publish booking created event
    publish_event("booking_created", str(db_obj.id))
    return db_obj


def update(db: Session, *, db_obj: Bookings, obj_in: BookingUpdate) -> Bookings:
    """
    Update a booking and its associated services.
    """
    # Update basic booking fields
    if obj_in.start_time is not None:
        db_obj.start_at = obj_in.start_time
    if obj_in.notes is not None:
        db_obj.notes = obj_in.notes
    if obj_in.status is not None:
        db_obj.status = obj_in.status

    # If services are being updated, we need to recalculate everything
    if obj_in.services is not None:
        # Remove existing booking services
        db.query(BookingServices).filter(BookingServices.booking_id == db_obj.id).delete()

        # Recalculate total duration and price
        total_duration, total_price = calc_service_params(db, obj_in.services, str(db_obj.company_id))
        db_obj.total_price = total_price

        # Update end time based on new start time and duration
        start_time = obj_in.start_time if obj_in.start_time is not None else db_obj.start_at
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
            current_start_time = db_service_obj.end_at
            db.add(db_service_obj)

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
