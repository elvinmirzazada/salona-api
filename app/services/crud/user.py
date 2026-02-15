import uuid
from typing import Optional, List
from datetime import datetime, timezone

from pydantic.v1 import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import CompanyUsers, CustomerStatusType
from app.models.models import Users, UserVerifications
from app.models.enums import VerificationStatus
from app.schemas import CompanyUser, User
from app.schemas.schemas import (
    UserCreate, UserUpdate
)
from app.core.datetime_utils import utcnow


async def get(db: AsyncSession, id: UUID4) -> Optional[tuple[Users, UUID4]]:
    stmt = (select(Users, CompanyUsers.company_id)
            .outerjoin(CompanyUsers, CompanyUsers.user_id == Users.id)
            .filter(Users.id == id))
    result = await db.execute(stmt)
    return result.first()


async def get_all(db: AsyncSession) -> List[Users]:
    stmt = select(Users)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_by_email(db: AsyncSession, email: str) -> Optional[Users]:
    stmt = select(Users).filter(Users.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create(db: AsyncSession, *, obj_in: UserCreate) -> Users:
    db_obj = Users(**obj_in.model_dump(exclude={'availabilities'}))
    db_obj.id = str(uuid.uuid4())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update(db: AsyncSession, *, db_obj: Users, obj_in: UserUpdate) -> Users:
    """Update user information"""
    update_data = obj_in.model_dump(exclude_unset=True)
    
    # If email is being updated, check if it's already in use by another user
    if 'email' in update_data and update_data['email']:
        existing_user = await get_by_email(db, email=update_data['email'])
        if existing_user and existing_user.id != db_obj.id:
            raise ValueError("Email is already in use by another user")
    
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    # Ensure updated_at is set to current UTC time
    db_obj.updated_at = utcnow()
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_verification_token(db: AsyncSession, token: str, type: str) -> Optional[UserVerifications]:
    """Get verification token by token string and type"""
    stmt = select(UserVerifications).filter(
        UserVerifications.token == token,
        UserVerifications.type == type
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def verify_token(db: AsyncSession, db_obj: UserVerifications) -> bool:
    """Mark verification token as verified and update user email_verified status"""
    try:
        db_obj.status = VerificationStatus.VERIFIED
        db_obj.used_at = utcnow()

        # Update user's email_verified status
        stmt = select(Users).filter(Users.id == db_obj.user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.email_verified = True
            user.status = CustomerStatusType.active
            user.updated_at = utcnow()
            db.add(user)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return True
    except Exception:
        await db.rollback()
        return False


async def get_company_users(db: AsyncSession, company_id: str) -> List[CompanyUser]:
    """
    Get all users for a company
    """
    stmt = (select(CompanyUsers)
            .options(selectinload(CompanyUsers.user))
            .join(Users, Users.id == CompanyUsers.user_id)
            .filter(Users.status == 'active',
                    CompanyUsers.company_id == company_id,
                    CompanyUsers.status == 'active'))
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users


async def get_company_by_user(db: AsyncSession, user_id: str) -> Optional[CompanyUsers]:
    stmt = select(CompanyUsers).filter(CompanyUsers.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
