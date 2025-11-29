from typing import List, Optional, Any
from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session
from app.models.models import UserAvailabilities, UserTimeOffs
from app.models.enums import AvailabilityType
from app.schemas.schemas import (
    TimeSlot,
    DailyAvailability,
    WeeklyAvailability,
    MonthlyAvailability,
    AvailabilityResponse
)

def get_user_availabilities(db: Session, user_id: str) -> List[UserAvailabilities]:
    """Get all availability entries for a user"""
    return list(db.query(UserAvailabilities).filter(UserAvailabilities.user_id == user_id,
                                                    UserAvailabilities.is_available == True).all())

def get_user_time_offs(
    db: Session,
    user_id: str,
    start_date: date,
    end_date: date
) -> List["UserTimeOffs"]:
    """Get all time-offs for a user within a date range"""
    return db.query(UserTimeOffs).filter(
        UserTimeOffs.user_id == user_id,
        UserTimeOffs.start_date <= end_date,
        UserTimeOffs.end_date >= start_date).all()

def get_all_availabilities(db: Session):
    """Get all available user availabilities"""
    return db.query(UserAvailabilities).filter(UserAvailabilities.is_available == True).all()

def get_all_time_offs(db: Session, start_date: date, end_date: date):
    """Get all time-offs within a date range"""
    return db.query(UserTimeOffs).filter(
        UserTimeOffs.start_date <= end_date,
        UserTimeOffs.end_date >= start_date
    ).all()

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

def get_daily_slots(target_date: date, availabilities: List[UserAvailabilities], time_offs: List[UserTimeOffs], bookings: List[Any]) -> DailyAvailability:
    day_of_week = target_date.weekday()
    day_availabilities = [a for a in availabilities if a.day_of_week == day_of_week]
    # Collect intervals to subtract (bookings and time-offs)
    subtract_intervals_list = []
    for time_off, user_id in time_offs:
        if time_off.start_date.date() <= target_date <= time_off.end_date.date():
            subtract_intervals_list.append((time(time_off.start_date.hour,time_off.start_date.minute),
                                            time(time_off.end_date.hour,time_off.end_date.minute)))
    for booking in bookings:
        if booking.start_at.date() == target_date:
            subtract_intervals_list.append((booking.start_at.time(), booking.end_at.time()))
    time_slots = []
    for avail in day_availabilities:
        available_intervals = subtract_intervals(avail.start_time, avail.end_time, subtract_intervals_list)
        for start, end in available_intervals:
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
    date_from: date
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
            daily = get_daily_slots(date_from, availabilities, time_offs, bookings)
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
                daily_slots.append(get_daily_slots(current_date, availabilities, time_offs, bookings))
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
                        daily_slots.append(get_daily_slots(week_date, availabilities, time_offs, bookings))
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