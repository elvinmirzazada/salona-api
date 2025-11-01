from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, UUID4, ConfigDict

from app.models.enums import MembershipPlanType, StatusType


# Membership Plan Schemas
class MembershipPlanBase(BaseModel):
    name: str
    plan_type: MembershipPlanType
    description: Optional[str] = None
    price: int
    url: Optional[str] = None
    duration_days: int = 30


class MembershipPlanCreate(MembershipPlanBase):
    pass


class MembershipPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    duration_days: Optional[int] = None
    status: Optional[StatusType] = None


class MembershipPlan(MembershipPlanBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID4
    status: StatusType
    created_at: datetime
    updated_at: datetime


# Company Membership Schemas
class CompanyMembershipBase(BaseModel):
    company_id: UUID4
    membership_plan_id: UUID4
    auto_renew: bool = True


class CompanyMembershipCreate(BaseModel):
    membership_plan_id: UUID4
    auto_renew: bool = True


class CompanyMembershipUpdate(BaseModel):
    auto_renew: Optional[bool] = None
    status: Optional[StatusType] = None


class CompanyMembership(CompanyMembershipBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID4
    status: StatusType
    start_date: datetime
    end_date: datetime
    created_at: datetime
    updated_at: datetime
    membership_plan: Optional[MembershipPlan] = None


# Membership Status Response
class MembershipStatusResponse(BaseModel):
    has_membership: bool
    plan_type: Optional[MembershipPlanType] = None
    plan_name: Optional[str] = None
    status: Optional[StatusType] = None
    end_date: Optional[datetime] = None
