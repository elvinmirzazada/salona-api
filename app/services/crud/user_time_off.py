from typing import List, Optional, Any
from datetime import date, datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic.v1 import UUID4
from sqlalchemy.orm import selectinload

from app.models import CompanyUsers
from app.models.models import UserTimeOffs
from app.schemas.schemas import TimeOffCreate, TimeOffUpdate
from app.core.datetime_utils import utcnow, ensure_utc


async def get_user_time_offs(
    db: AsyncSession,
    company_id: str,
    start_date: datetime = None,
    end_date: datetime = None
) -> List[UserTimeOffs]:
    """
    Get all time-offs for a user with optional date filtering
    """
    stmt = (select(UserTimeOffs)
            .options(selectinload(UserTimeOffs.user))
            .join(CompanyUsers, CompanyUsers.user_id == UserTimeOffs.user_id)
            .filter(CompanyUsers.company_id == company_id))

    if start_date and end_date:
        # Ensure dates are in UTC
        start_date_utc = datetime.combine(start_date, datetime.min.time())
        end_date_utc = datetime.combine(end_date, datetime.max.time())
        # Get time offs that overlap with the given date range
        stmt = stmt.filter(
            UserTimeOffs.start_date <= end_date_utc,
            UserTimeOffs.end_date >= start_date_utc
        )
    
    result = await db.execute(stmt)
    return result.scalars().all()


async def get(db: AsyncSession, time_off_id: UUID4) -> Optional[UserTimeOffs]:
    """
    Get a specific time off by ID
    """
    stmt = select(UserTimeOffs).filter(UserTimeOffs.id == time_off_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create(db: AsyncSession, *, obj_in: TimeOffCreate, company_id: Optional[str]) -> UserTimeOffs:
    """
    Create a new time off period for a user

    If company_id is provided, validates that the user belongs to that company
    """
    # Validate that end_date is not before start_date
    if obj_in.end_date < obj_in.start_date:
        raise ValueError("End date cannot be before start date")
    start_date_utc = ensure_utc(obj_in.start_date)
    end_date_utc = ensure_utc(obj_in.end_date)
    # Check if company_id is provided, validate user belongs to this company
    if company_id:
        stmt = select(CompanyUsers).filter(
            CompanyUsers.user_id == obj_in.user_id,
            CompanyUsers.company_id == company_id
        )
        result = await db.execute(stmt)
        company_user = result.scalar_one_or_none()

        if not company_user:
            raise ValueError(f"User {obj_in.user_id} does not belong to company {company_id}")

    db_obj = UserTimeOffs(
        # id=uuid.uuid4(),
        user_id=obj_in.user_id,
        start_date=start_date_utc,
        end_date=end_date_utc,
        reason=obj_in.reason

    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj, )
    return db_obj


async def update(db: AsyncSession, *, db_obj: UserTimeOffs, obj_in: TimeOffUpdate) -> UserTimeOffs:
    """
    Update an existing time off period
    """
    # Update fields if provided
    if obj_in.start_date is not None:
        db_obj.start_date = obj_in.start_date
    update_data = obj_in.model_dump(exclude_unset=True)
    if obj_in.end_date is not None:
        db_obj.end_date = obj_in.end_date
        update_data['end_date'] = ensure_utc(update_data['end_date'])
    if obj_in.reason is not None:
        db_obj.reason = obj_in.reason
    
    # Validate that end_date is not before start_date after updates
    if db_obj.end_date < db_obj.start_date:
        raise ValueError("End date cannot be before start date")
    db_obj.updated_at = utcnow()

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, *, time_off_id: UUID4) -> bool:
    """
    Delete a time off period
    """
    stmt = select(UserTimeOffs).filter(UserTimeOffs.id == time_off_id)
    result = await db.execute(stmt)
    db_obj = result.scalar_one_or_none()

    if not db_obj:
        return False
    
    await db.delete(db_obj)
    await db.commit()
    return True


async def check_overlapping_time_offs(
    db: AsyncSession,
    user_id: UUID4,
    start_date: datetime,
    end_date: datetime,
    exclude_id: UUID4 = None
) -> bool:
    """
    Check if a new time off period overlaps with existing ones
    Returns True if there are overlaps, False otherwise
    """
    stmt = select(UserTimeOffs).filter(
        UserTimeOffs.user_id == user_id,
        UserTimeOffs.start_date <= end_date,
        UserTimeOffs.end_date >= start_date
    )

    # Exclude the current time off if updating
    if exclude_id:
        stmt = stmt.filter(UserTimeOffs.id != exclude_id)

    result = await db.execute(stmt)
    count = len(result.scalars().all())
    return count > 0


async def get_company_user_time_offs(
        db: AsyncSession,
        company_id: str,
        start_date: date = None,
        end_date: date = None
) -> List[UserTimeOffs]:
    """
    Get all time-offs for all users in a company with optional date filtering
    """
    stmt = (select(UserTimeOffs)
            .join(CompanyUsers, CompanyUsers.user_id == UserTimeOffs.user_id)
            .filter(CompanyUsers.company_id == company_id))

    if start_date and end_date:
        # Ensure dates are in UTC
        start_date_utc = datetime.combine(start_date, datetime.min.time())
        end_date_utc = datetime.combine(end_date, datetime.max.time())
        # Get time offs that overlap with the given date range
        stmt = stmt.filter(
            UserTimeOffs.start_date <= end_date_utc,
            UserTimeOffs.end_date >= start_date_utc
        )

    result = await db.execute(stmt)
    return list(result.scalars().all())
