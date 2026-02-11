from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models.models import MembershipPlans, CompanyMemberships
from app.models.enums import MembershipPlanType, StatusType
from app.schemas.membership import (
    MembershipPlanCreate, MembershipPlanUpdate,
    CompanyMembershipCreate, CompanyMembershipUpdate
)
from app.core.datetime_utils import utcnow, ensure_utc


class MembershipPlanCRUD:
    """CRUD operations for membership plans"""

    async def create(self, db: AsyncSession, *, obj_in: MembershipPlanCreate) -> MembershipPlans:
        """Create a new membership plan"""
        db_obj = MembershipPlans(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get(self, db: AsyncSession, *, id: str) -> Optional[MembershipPlans]:
        """Get membership plan by ID"""
        stmt = select(MembershipPlans).filter(MembershipPlans.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_type(self, db: AsyncSession, *, plan_type: MembershipPlanType) -> Optional[MembershipPlans]:
        """Get membership plan by type"""
        stmt = select(MembershipPlans).filter(
            MembershipPlans.plan_type == plan_type,
            MembershipPlans.status == StatusType.active
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, db: AsyncSession, *, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[MembershipPlans]:
        """Get all membership plans"""
        stmt = select(MembershipPlans)
        if active_only:
            stmt = stmt.filter(MembershipPlans.status == StatusType.active)
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, *, db_obj: MembershipPlans, obj_in: MembershipPlanUpdate) -> MembershipPlans:
        """Update a membership plan"""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Ensure updated_at is set to current UTC time
        db_obj.updated_at = utcnow()

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: str) -> Optional[MembershipPlans]:
        """Soft delete membership plan"""
        stmt = select(MembershipPlans).filter(MembershipPlans.id == id)
        result = await db.execute(stmt)
        db_obj = result.scalar_one_or_none()

        if db_obj:
            db_obj.status = StatusType.inactive
            db_obj.updated_at = utcnow()
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
        return db_obj


class CompanyMembershipCRUD:
    """CRUD operations for company memberships"""

    async def create(self, db: AsyncSession, *, company_id: str, obj_in: CompanyMembershipCreate) -> CompanyMemberships:
        """Create a new company membership subscription"""
        # Get the membership plan to calculate end date
        stmt = select(MembershipPlans).filter(MembershipPlans.id == obj_in.membership_plan_id)
        result = await db.execute(stmt)
        plan = result.scalar_one_or_none()

        if not plan:
            raise ValueError("Membership plan not found")

        # Deactivate any existing active memberships
        stmt = select(CompanyMemberships).filter(
            CompanyMemberships.company_id == company_id,
            CompanyMemberships.status == StatusType.active
        )
        result = await db.execute(stmt)
        existing = result.scalars().all()

        for membership in existing:
            membership.status = StatusType.inactive
            db.add(membership)

        # Calculate end date
        start_date = utcnow()
        end_date = start_date + timedelta(days=int(str(plan.duration_days)))

        db_obj = CompanyMemberships(
            company_id=company_id,
            membership_plan_id=obj_in.membership_plan_id,
            auto_renew=obj_in.auto_renew,
            start_date=start_date,
            end_date=end_date,
            status=StatusType.active
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get(self, db: AsyncSession, *, id: str) -> Optional[CompanyMemberships]:
        """Get company membership by ID"""
        stmt = select(CompanyMemberships).filter(CompanyMemberships.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_membership(self, db: AsyncSession, *, company_id: str) -> Optional[CompanyMemberships]:
        """Get company's active membership"""
        # Use naive datetime since DB expects TIMESTAMP WITHOUT TIME ZONE
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

        stmt = (select(CompanyMemberships)
            .options(selectinload(CompanyMemberships.membership_plan))
            .filter(
                CompanyMemberships.company_id == company_id,
                CompanyMemberships.status == StatusType.active,
                CompanyMemberships.end_date > now_naive
        ))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_company_memberships(self, db: AsyncSession, *, company_id: str, skip: int = 0, limit: int = 100) -> List[CompanyMemberships]:
        """Get all memberships for a company"""
        stmt = select(CompanyMemberships).filter(
            CompanyMemberships.company_id == company_id
        ).order_by(CompanyMemberships.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, *, db_obj: CompanyMemberships, obj_in: CompanyMembershipUpdate) -> CompanyMemberships:
        """Update company membership"""
        update_data = obj_in.model_dump(exclude_unset=True)

        # Ensure datetime fields are in UTC
        if 'start_date' in update_data:
            update_data['start_date'] = ensure_utc(update_data['start_date'])
        if 'end_date' in update_data:
            update_data['end_date'] = ensure_utc(update_data['end_date'])

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Ensure updated_at is set to current UTC time
        db_obj.updated_at = utcnow()

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def cancel(self, db: AsyncSession, *, id: str) -> Optional[CompanyMemberships]:
        """Cancel a company membership"""
        stmt = select(CompanyMemberships).filter(CompanyMemberships.id == id)
        result = await db.execute(stmt)
        obj = result.scalar_one_or_none()

        if obj:
            obj.status = StatusType.inactive
            obj.auto_renew = False
            db.add(obj)
            await db.commit()
            await db.refresh(obj)
        return obj


# Create singleton instances
membership_plan = MembershipPlanCRUD()
company_membership = CompanyMembershipCRUD()
