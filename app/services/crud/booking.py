from datetime import timedelta, timezone
from typing import List, Optional, Any
from datetime import date, datetime

from pydantic.v1 import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select, delete
from sqlalchemy.orm import selectinload

from app.models import BookingServices, Customers, CategoryServices
from app.models.models import Bookings
from app.models.enums import BookingStatus
from app.schemas import BookingServiceRequest
from app.schemas.schemas import BookingCreate, BookingUpdate
from app.services.crud import service
from app.core.redis_client import publish_event
from app.services.crud.company import get_company_users
from app.core.datetime_utils import utcnow, ensure_utc


async def get(db: AsyncSession, id: UUID4) -> Optional[Bookings]:
    stmt = select(Bookings).filter(Bookings.id == id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[type[Bookings]]:
    stmt = select(Bookings).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_user_bookings_in_range(db: AsyncSession, user_id: str, start_date: Any, end_date: Any) -> list["Bookings"]:
    stmt = (select(Bookings)
            .join(BookingServices)
            .filter(
                BookingServices.user_id == user_id,
                Bookings.start_at >= start_date,
                Bookings.end_at <= end_date
            ))
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_all_bookings_in_range(db: AsyncSession, start_date: date, end_date: date):
    # Join Bookings and BookingServices, return tuples of (booking, user_id)
    stmt = (select(Bookings, BookingServices.user_id)
            .join(BookingServices, Bookings.id == BookingServices.booking_id)
            .filter(
                Bookings.start_at >= start_date,
                Bookings.end_at <= end_date
            ))
    result = await db.execute(stmt)
    return result.all()


async def get_all_bookings_in_range_by_company(db: AsyncSession, company_id: str, start_date: date, end_date: date):
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    stmt = (select(Bookings)
            .options(
        selectinload(Bookings.booking_services).selectinload(BookingServices.assigned_staff),
                selectinload(Bookings.customer)
            )
            .filter(
                Bookings.company_id == company_id,
                Bookings.start_at >= start_datetime,
                Bookings.end_at <= end_datetime,
                Bookings.status.in_(['scheduled', 'confirmed', 'completed', 'no_show', 'cancelled'])
            ))
    result = await db.execute(stmt)
    bookings = result.scalars().all()
    return bookings

async def check_staff_availability(db: AsyncSession, user_id: UUID4, start_time: datetime, end_time: datetime, exclude_booking_id: Optional[UUID4] = None) -> tuple[bool, Optional[str]]:
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
    stmt = (select(BookingServices)
            .join(Bookings)
            .filter(
                BookingServices.user_id == user_id,
                Bookings.status.in_([BookingStatus.SCHEDULED, BookingStatus.CONFIRMED]),
                # Check for time overlap: (start_time < existing_end AND end_time > existing_start)
                BookingServices.start_at < end_time,
                BookingServices.end_at > start_time
            ))

    # Exclude the current booking if updating
    if exclude_booking_id:
        stmt = stmt.filter(Bookings.id != exclude_booking_id)

    result = await db.execute(stmt)
    conflicting_bookings = result.scalars().all()

    if conflicting_bookings:
        conflict = conflicting_bookings[0]
        conflict_message = f"Staff member is not available. There is a conflicting booking from {conflict.start_at.strftime('%H:%M')} to {conflict.end_at.strftime('%H:%M')}"
        return False, conflict_message
    
    return True, None


async def calc_service_params(db: AsyncSession, services: List[BookingServiceRequest], company_id: str = None) -> tuple[int, int]:
    total_duration = 0
    total_price = 0

    for srv in services:
        selected_srv = await service.get_service(db, srv.category_service_id, company_id)
        total_duration += selected_srv.duration
        total_price += int(selected_srv.discount_price or selected_srv.price)

    return total_duration, total_price


async def create(db: AsyncSession, *, obj_in: BookingCreate, customer_id: UUID4) -> Bookings:
    total_duration, total_price = await calc_service_params(db, obj_in.services, obj_in.company_id)

    db_obj = Bookings(
        customer_id=customer_id,
        company_id=obj_in.company_id,
        start_at=obj_in.start_time,
        end_at=obj_in.start_time + timedelta(minutes=total_duration),
        total_price=total_price,
        notes=obj_in.notes,
        status=BookingStatus.CONFIRMED
    )
    db.add(db_obj)
    await db.commit()

    current_start_time = obj_in.start_time
    for srv in obj_in.services:
        if not srv.user_id:
            company_users = await get_company_users(db, str(obj_in.company_id))
            srv.user_id = company_users[0].user_id
        duration, _ = await calc_service_params(db, [srv], obj_in.company_id)
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

    await db.commit()
    await db.refresh(db_obj)
    # Publish booking created event
    # publish_event("booking_created", str(db_obj.id))
    return db_obj


async def update(db: AsyncSession, *, db_obj: Bookings, obj_in: BookingUpdate) -> Bookings:
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
            # Remove timezone info for DB storage
            db_obj.start_at = obj_in.start_time.replace(tzinfo=None) if obj_in.start_time.tzinfo else obj_in.start_time

        # Remove existing booking services
        stmt = delete(BookingServices).filter(BookingServices.booking_id == db_obj.id)
        await db.execute(stmt)

        # Recalculate total duration and price
        total_duration, total_price = await calc_service_params(db, obj_in.services, str(db_obj.company_id))
        db_obj.total_price = total_price

        # Update end time based on new start time and duration
        start_time = db_obj.start_at
        db_obj.end_at = start_time + timedelta(minutes=total_duration)

        # Create new booking services
        current_start_time = start_time
        for srv in obj_in.services:
            duration, _ = await calc_service_params(db, [srv], str(db_obj.company_id))
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

    # If only start_time is being updated (without services)
    elif obj_in.start_time is not None:
        # Get existing booking services
        stmt = select(BookingServices).filter(
            BookingServices.booking_id == db_obj.id
        ).order_by(BookingServices.start_at)
        result = await db.execute(stmt)
        existing_services = result.scalars().all()

        # Remove timezone info before calculating time difference
        new_start_time = obj_in.start_time.replace(tzinfo=None) if obj_in.start_time.tzinfo else obj_in.start_time
        old_start_time = db_obj.start_at

        # Calculate the time difference
        time_diff = new_start_time - old_start_time

        # Update booking start and end times
        db_obj.start_at = new_start_time
        db_obj.end_at = db_obj.end_at + time_diff

        # Update all existing booking services with the new times
        current_start_time = new_start_time
        for booking_service in existing_services:
            # Calculate the duration of this service
            service_duration = booking_service.end_at - booking_service.start_at

            # Update the service times
            booking_service.start_at = current_start_time
            booking_service.end_at = current_start_time + service_duration

            current_start_time = booking_service.end_at
            db.add(booking_service)

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def cancel(db: AsyncSession, *, booking_id: UUID4) -> Optional[Bookings]:
    """
    Cancel a booking by setting its status to CANCELLED.
    Returns the updated booking or None if booking not found.
    """
    stmt = select(Bookings).filter(Bookings.id == booking_id)
    result = await db.execute(stmt)
    db_obj = result.scalar_one_or_none()

    if db_obj:
        db_obj.status = BookingStatus.CANCELLED
        db.add(db_obj)
        await db.flush()  # Flush to get the updated object but don't commit yet
        return db_obj
    return None


async def confirm(db: AsyncSession, *, booking_id: UUID4) -> Optional[Bookings]:
    """
    Confirm a booking by setting its status to CONFIRMED.
    Returns the updated booking or None if booking not found.
    """
    stmt = select(Bookings).filter(Bookings.id == booking_id)
    result = await db.execute(stmt)
    db_obj = result.scalar_one_or_none()

    if db_obj:
        db_obj.status = BookingStatus.CONFIRMED
        db.add(db_obj)
        await db.flush()  # Flush to get the updated object but don't commit yet
        return db_obj
    return None


async def complete(db: AsyncSession, *, booking_id: UUID4) -> Optional[Bookings]:
    """
    Complete a booking by setting its status to COMPLETED.
    Returns the updated booking or None if booking not found.
    """
    stmt = select(Bookings).filter(Bookings.id == booking_id)
    result = await db.execute(stmt)
    db_obj = result.scalar_one_or_none()

    if db_obj:
        db_obj.status = BookingStatus.COMPLETED
        db.add(db_obj)
        await db.flush()  # Flush to get the updated object but don't commit yet
        return db_obj
    return None


async def no_show(db: AsyncSession, *, booking_id: UUID4) -> Optional[Bookings]:
    """
    Mark a booking as NO_SHOW when the customer doesn't show up.
    Returns the updated booking or None if booking not found.
    """
    stmt = select(Bookings).filter(Bookings.id == booking_id)
    result = await db.execute(stmt)
    db_obj = result.scalar_one_or_none()

    if db_obj:
        db_obj.status = BookingStatus.NO_SHOW
        db.add(db_obj)
        await db.flush()  # Flush to get the updated object but don't commit yet
        return db_obj
    return None

