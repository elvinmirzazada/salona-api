from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.models.models import MembershipPlans, CompanyMemberships
from app.models.enums import MembershipPlanType, StatusType
from app.schemas.membership import (
    MembershipPlanCreate, MembershipPlanUpdate,
    CompanyMembershipCreate, CompanyMembershipUpdate
)
from app.core.datetime_utils import utcnow, ensure_utc


class MembershipPlanCRUD:
    """CRUD operations for membership plans"""

    def create(self, db: Session, *, obj_in: MembershipPlanCreate) -> MembershipPlans:
        """Create a new membership plan"""
        db_obj = MembershipPlans(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, *, id: str) -> Optional[MembershipPlans]:
        """Get membership plan by ID"""
        return db.query(MembershipPlans).filter(MembershipPlans.id == id).first()

    def get_by_type(self, db: Session, *, plan_type: MembershipPlanType) -> Optional[MembershipPlans]:
        """Get membership plan by type"""
        return db.query(MembershipPlans).filter(
            MembershipPlans.plan_type == plan_type,
            MembershipPlans.status == StatusType.active
        ).first()

    def get_all(self, db: Session, *, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[MembershipPlans]:
        """Get all membership plans"""
        query = db.query(MembershipPlans)
        if active_only:
            query = query.filter(MembershipPlans.status == StatusType.active)
        return query.offset(skip).limit(limit).all()

    def update(self, db: Session, *, db_obj: MembershipPlans, obj_in: MembershipPlanUpdate) -> MembershipPlans:
        """Update a membership plan"""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Ensure updated_at is set to current UTC time
        db_obj.updated_at = utcnow()

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: str) -> Optional[MembershipPlans]:
        """Soft delete membership plan"""
        db_obj = db.query(MembershipPlans).filter(MembershipPlans.id == id).first()
        if db_obj:
            db_obj.status = StatusType.inactive
            db_obj.updated_at = utcnow()
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        return db_obj


class CompanyMembershipCRUD:
    """CRUD operations for company memberships"""

    def create(self, db: Session, *, company_id: str, obj_in: CompanyMembershipCreate) -> CompanyMemberships:
        """Create a new company membership subscription"""
        # Get the membership plan to calculate end date
        plan = db.query(MembershipPlans).filter(MembershipPlans.id == obj_in.membership_plan_id).first()
        if not plan:
            raise ValueError("Membership plan not found")

        # Deactivate any existing active memberships
        existing = db.query(CompanyMemberships).filter(
            CompanyMemberships.company_id == company_id,
            CompanyMemberships.status == StatusType.active
        ).all()
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
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, *, id: str) -> Optional[CompanyMemberships]:
        """Get company membership by ID"""
        return db.query(CompanyMemberships).filter(CompanyMemberships.id == id).first()

    def get_active_membership(self, db: Session, *, company_id: str) -> Optional[CompanyMemberships]:
        """Get company's active membership"""
        return db.query(CompanyMemberships).filter(
            CompanyMemberships.company_id == company_id,
            CompanyMemberships.status == StatusType.active,
            CompanyMemberships.end_date > datetime.now(timezone.utc)
        ).first()

    def get_company_memberships(self, db: Session, *, company_id: str, skip: int = 0, limit: int = 100) -> List[CompanyMemberships]:
        """Get all memberships for a company"""
        return db.query(CompanyMemberships).filter(
            CompanyMemberships.company_id == company_id
        ).order_by(CompanyMemberships.created_at.desc()).offset(skip).limit(limit).all()

    def update(self, db: Session, *, db_obj: CompanyMemberships, obj_in: CompanyMembershipUpdate) -> CompanyMemberships:
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
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def cancel(self, db: Session, *, id: str) -> Optional[CompanyMemberships]:
        """Cancel a company membership"""
        obj = db.query(CompanyMemberships).filter(CompanyMemberships.id == id).first()
        if obj:
            obj.status = StatusType.inactive
            obj.auto_renew = False
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj


# Create singleton instances
membership_plan = MembershipPlanCRUD()
company_membership = CompanyMembershipCRUD()
