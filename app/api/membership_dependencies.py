from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.models.enums import MembershipPlanType
from app.services.crud import membership as crud_membership
from app.api.dependencies import get_current_company_id


def get_company_membership_plan(
    company_id: str = Depends(get_current_company_id),
    db: Session = Depends(get_db)
) -> Optional[MembershipPlanType]:
    """Get the current company's membership plan type if they have an active membership."""
    membership = crud_membership.company_membership.get_active_membership(
        db, company_id=company_id
    )
    if membership and membership.membership_plan:
        return membership.membership_plan.plan_type
    return None


def require_company_membership(
    allowed_plans: list[MembershipPlanType] = None,
    min_plan: MembershipPlanType = None
):
    """
    Dependency factory to require company membership.
    
    Args:
        allowed_plans: Specific list of allowed plan types
        min_plan: Minimum plan type required (standard < premium < vip)
    
    Usage:
        @router.post("/premium-feature")
        async def premium_feature(
            plan: MembershipPlanType = Depends(require_company_membership(min_plan=MembershipPlanType.PREMIUM))
        ):
            ...
    """
    plan_hierarchy = {
        MembershipPlanType.STANDARD: 1,
        MembershipPlanType.PREMIUM: 2,
        MembershipPlanType.VIP: 3
    }
    
    async def membership_checker(
        company_id: str = Depends(get_current_company_id),
        db: Session = Depends(get_db)
    ) -> MembershipPlanType:
        membership = crud_membership.company_membership.get_active_membership(
            db, company_id=company_id
        )
        
        if not membership or not membership.membership_plan:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active membership required to access this feature"
            )
        
        current_plan = membership.membership_plan.plan_type
        
        # Check against specific allowed plans
        if allowed_plans and current_plan not in allowed_plans:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires one of the following memberships: {', '.join([str(p.value) for p in allowed_plans])}"
            )
        
        # Check against minimum plan level
        if min_plan:
            if plan_hierarchy.get(current_plan, 0) < plan_hierarchy.get(min_plan, 0):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires at least {min_plan.value} membership"
                )
        
        return current_plan
    
    return membership_checker
