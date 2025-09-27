from datetime import timedelta
from typing import List, Optional, Any
from datetime import date

from pydantic.v1 import UUID4
from sqlalchemy.orm import Session

from app.models import BookingServices, Customers
from app.models.models import Bookings
from app.schemas import BookingServiceRequest
from app.schemas.schemas import BookingCreate
from app.services.crud import service


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
        Bookings.end_at <= end_date
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
    return db_obj