from typing import List, Optional, Any
from datetime import datetime, date, time, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import uuid
from app.models.models import UserAvailabilities, UserTimeOffs
from app.models.enums import AvailabilityType
from app.schemas.schemas import (
    TimeSlot,
    DailyAvailability,
    WeeklyAvailability,
    MonthlyAvailability,
    AvailabilityResponse,
    UserAvailabilityCreate
)
from app.core.datetime_utils import utcnow, convert_utc_to_timezone


async def create_user_availability(db: AsyncSession, user_id: str, availability_in: UserAvailabilityCreate) -> UserAvailabilities:
    """Create a new availability entry for a user"""
    db_availability = UserAvailabilities(
        id=str(uuid.uuid4()),
        user_id=user_id,
        day_of_week=availability_in.day_of_week,
        start_time=availability_in.start_time,
        end_time=availability_in.end_time,
        is_available=availability_in.is_available,
        created_at=utcnow(),
        updated_at=utcnow()
    )
    db.add(db_availability)
    await db.commit()
    await db.refresh(db_availability)
    return db_availability


async def bulk_create_user_availabilities(db: AsyncSession, user_id: str, availabilities: List[UserAvailabilityCreate]) -> List[UserAvailabilities]:
    """Create multiple availability entries for a user"""
    db_availabilities = []
    for availability_in in availabilities:
        db_availability = UserAvailabilities(
            id=str(uuid.uuid4()),
            user_id=user_id,
            day_of_week=availability_in.day_of_week,
            start_time=availability_in.start_time,
            end_time=availability_in.end_time,
            is_available=availability_in.is_available,
            created_at=utcnow(),
            updated_at=utcnow()
        )
        db_availabilities.append(db_availability)
    
    db.add_all(db_availabilities)
    await db.commit()
    for db_availability in db_availabilities:
        await db.refresh(db_availability)
    return db_availabilities


async def delete_user_availabilities(db: AsyncSession, user_id: str) -> bool:
    """Delete all availability entries for a user"""
    stmt = delete(UserAvailabilities).filter(UserAvailabilities.user_id == user_id)
    await db.execute(stmt)
    await db.commit()
    return True


async def update_user_availabilities(db: AsyncSession, user_id: str, availabilities: List[UserAvailabilityCreate]) -> List[UserAvailabilities]:
    """Replace all availability entries for a user with new ones"""
    # Delete existing availabilities
    await delete_user_availabilities(db, user_id)

    # Create new availabilities
    if availabilities:
        return await bulk_create_user_availabilities(db, user_id, availabilities)
    return []


async def get_user_availabilities(db: AsyncSession, user_id: str) -> List[UserAvailabilities]:
    """Get all availability entries for a user"""
    stmt = select(UserAvailabilities).filter(
        UserAvailabilities.user_id == user_id,
        UserAvailabilities.is_available == True
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_user_time_offs(
    db: AsyncSession,
    user_id: str,
    start_date: date,
    end_date: date
) -> List["UserTimeOffs"]:
    """Get all time-offs for a user within a date range"""
    stmt = select(UserTimeOffs).filter(
        UserTimeOffs.user_id == user_id,
        UserTimeOffs.start_date <= end_date,
        UserTimeOffs.end_date >= start_date
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_all_availabilities(db: AsyncSession):
    """Get all available user availabilities"""
    stmt = select(UserAvailabilities).filter(UserAvailabilities.is_available == True)
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_all_time_offs(db: AsyncSession, start_date: date, end_date: date):
    """Get all time-offs within a date range"""
    stmt = select(UserTimeOffs).filter(
        UserTimeOffs.start_date <= end_date,
        UserTimeOffs.end_date >= start_date
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

def subtract_intervals(base_start: time, base_end: time, intervals: List[tuple]) -> List[tuple]:
    """Subtract intervals (bookings/time-offs) from a base interval. Returns list of available intervals."""
    result = [(base_start, base_end)]
    for interval_start, interval_end in intervals:
        new_result = []
        for avail_start, avail_end in result:
            # If no overlap, keep as is
            if interval_end <= avail_start or interval_start >= avail_end:
                new_result.append((avail_start, avail_end))
            else:
                # Overlap: split interval
                if interval_start > avail_start:
                    new_result.append((avail_start, interval_start))
                if interval_end < avail_end:
                    new_result.append((interval_end, avail_end))
        result = new_result
    return result

def get_daily_slots(target_date: date, availabilities: List[UserAvailabilities], time_offs: List[UserTimeOffs], bookings: List[Any], service_duration_minutes: Optional[int] = None, company_timezone: str = "UTC") -> DailyAvailability:
    day_of_week = target_date.weekday()
    day_availabilities = [a for a in availabilities if a.day_of_week == day_of_week]
    # Collect intervals to subtract (bookings and time-offs)
    subtract_intervals_list = []

    # Process time-offs: convert from UTC to company timezone
    for time_off, user_id in time_offs:
        # Convert UTC datetime to company timezone
        start_date_local = convert_utc_to_timezone(time_off.start_date, company_timezone)
        end_date_local = convert_utc_to_timezone(time_off.end_date, company_timezone)

        if start_date_local.date() <= target_date <= end_date_local.date():
            subtract_intervals_list.append((time(start_date_local.hour, start_date_local.minute),
                                            time(end_date_local.hour, end_date_local.minute)))

    # Process bookings: convert from UTC to company timezone
    for booking in bookings:
        # Convert UTC datetime to company timezone
        start_at_local = convert_utc_to_timezone(booking.start_at, company_timezone)
        end_at_local = convert_utc_to_timezone(booking.end_at, company_timezone)

        if start_at_local.date() == target_date:
            subtract_intervals_list.append((start_at_local.time(), end_at_local.time()))

    time_slots = []
    for avail in day_availabilities:
        available_intervals = subtract_intervals(avail.start_time, avail.end_time, subtract_intervals_list)
        for start, end in available_intervals:
            # If service_duration_minutes is provided, filter slots that don't have enough time
            if service_duration_minutes:
                # Calculate the duration of this slot in minutes
                start_datetime = datetime.combine(target_date, start)
                end_datetime = datetime.combine(target_date, end)
                slot_duration_minutes = (end_datetime - start_datetime).total_seconds() / 60
                
                # Only include slots that have enough time for the service
                # Adjust end_time to be service_duration_minutes before the actual end
                if slot_duration_minutes >= service_duration_minutes:
                    # Calculate the last possible start time
                    last_start_time = (datetime.combine(target_date, end) - timedelta(minutes=service_duration_minutes)).time()
                    if start < last_start_time:
                        time_slots.append(TimeSlot(
                            start_time=start,
                            end_time=last_start_time,
                            is_available=True
                        ))
            else:
                # No service duration provided, include the full slot
                if start < end:
                    time_slots.append(TimeSlot(
                        start_time=start,
                        end_time=end,
                        is_available=True
                    ))
    return DailyAvailability(
        date=target_date,
        time_slots=time_slots
    )

def calculate_availability(
    availabilities: List[UserAvailabilities],
    time_offs: List[UserTimeOffs],
    bookings: List[Any],
    availability_type: AvailabilityType,
    date_from: date,
    service_duration_minutes: Optional[int] = None,
    company_timezone: str = "UTC"
) -> AvailabilityResponse:
    """Calculate availability based on working hours, time-offs, and bookings"""
    try:
        if not availabilities:
            return AvailabilityResponse(
                user_id=None,
                availability_type=availability_type,
                daily=None,
                weekly=None,
                monthly=None
            )
        if availability_type == AvailabilityType.DAILY:
            daily = get_daily_slots(date_from, availabilities, time_offs, bookings, service_duration_minutes, company_timezone)
            return AvailabilityResponse(
                user_id=str(availabilities[0].user_id),
                availability_type=availability_type,
                daily=daily
            )
        elif availability_type == AvailabilityType.WEEKLY:
            week_start = date_from
            week_end = week_start + timedelta(days=6)
            daily_slots = []
            current_date = week_start
            while current_date <= week_end:
                daily_slots.append(get_daily_slots(current_date, availabilities, time_offs, bookings, service_duration_minutes, company_timezone))
                current_date += timedelta(days=1)
            weekly = WeeklyAvailability(
                week_start_date=week_start,
                week_end_date=week_end,
                daily_slots=daily_slots
            )
            return AvailabilityResponse(
                user_id=str(availabilities[0].user_id),
                availability_type=availability_type,
                weekly=weekly
            )
        else:  # MONTHLY
            month_start = date_from.replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
            weekly_slots = []
            current_date = month_start
            while current_date <= month_end:
                week_start = current_date - timedelta(days=current_date.weekday())
                week_end = min(week_start + timedelta(days=6), month_end)
                daily_slots = []
                week_date = week_start
                while week_date <= week_end:
                    if month_start <= week_date <= month_end:
                        daily_slots.append(get_daily_slots(week_date, availabilities, time_offs, bookings, service_duration_minutes, company_timezone))
                    week_date += timedelta(days=1)
                weekly_slots.append(WeeklyAvailability(
                    week_start_date=week_start,
                    week_end_date=week_end,
                    daily_slots=daily_slots
                ))
                current_date = week_end + timedelta(days=1)
            monthly = MonthlyAvailability(
                month=date_from.month,
                year=date_from.year,
                weekly_slots=weekly_slots
            )

            return AvailabilityResponse(
                user_id=str(availabilities[0].user_id),
                availability_type=availability_type,
                monthly=monthly
            )
    except Exception as ex:
        print(f"Error calculating availability: {ex}")
        raise