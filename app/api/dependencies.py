from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db
from app.schemas import User
from app.services.auth import get_current_id, verify_token
from app.services.crud import user as crud_user, customer as crud_customer, company as crud_company
from app.models.models import Users, Customers, CompanyUsers
from app.models.enums import CompanyRoleType


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Users:
    """Get the current authenticated user from JWT token in HTTP-only cookie."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract access token from HTTP-only cookie
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise credentials_exception

    # Extract user ID from token (this will raise HTTPException with specific message if token is expired)
    user_id = get_current_id(access_token)
    if user_id is None:
        raise credentials_exception

    # Get user from database
    user, company_id = await crud_user.get(db, id=user_id)
    if user is None:
        raise credentials_exception

    user.company_id = company_id
    return user


async def get_current_customer(
        request: Request,
        db: AsyncSession = Depends(get_db)
) -> Customers:
    """Get the current authenticated customer from JWT token in HTTP-only cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Extract access token from HTTP-only cookie
        access_token = request.cookies.get("access_token")
        if not access_token:
            raise credentials_exception

        # Extract customer ID from token
        customer_id = get_current_id(access_token)
        if customer_id is None:
            raise credentials_exception

    except Exception:
        raise credentials_exception

    # Get customer from database
    customer = await crud_customer.get(db, id=customer_id)

    if customer is None:
        raise credentials_exception

    return customer


def get_token_payload(
        request: Request
) -> dict:
    """Extract and return the payload from the JWT token in HTTP-only cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Extract access token from HTTP-only cookie
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise credentials_exception

    # Extract payload from token (this will raise HTTPException with specific message if token is expired)
    payload = verify_token(access_token)
    if payload is None:
        raise credentials_exception

    return payload


def get_current_company_id(token_payload: dict = Depends(get_token_payload)) -> str:
    company_id = token_payload.get("company_id")
    if not company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company ID not found in token"
        )
    return company_id


async def get_current_active_user(
    current_user: Users = Depends(get_current_user)
) -> Users:
    """Get the current active user (can be extended for status checks)."""
    # Here you can add additional checks like account status, subscription, etc.
    return current_user


async def get_current_company_user(
        current_user: Users = Depends(get_current_user),
        company_id: str = Depends(get_current_company_id),
        db: AsyncSession = Depends(get_db)
) -> CompanyUsers:
    """Get the current active user (can be extended for status checks)."""
    # Here you can add additional checks like account status, subscription, etc.
    company_user = await crud_company.get_company_user(db, user_id=current_user.id, company_id=company_id)

    return company_user


async def get_current_active_customer(
    current_customer: Customers = Depends(get_current_customer)
) -> Customers:
    """Get the current active customer (can be extended for status checks)."""
    # Here you can add additional checks like account status, subscription, etc.
    return current_customer


async def get_current_user_role(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    company_id: str = Depends(get_current_company_id)
) -> CompanyRoleType:
    """Get the current user's role in the company."""
    from sqlalchemy import select

    stmt = select(CompanyUsers).filter(
        CompanyUsers.user_id == current_user.id,
        CompanyUsers.company_id == company_id
    )
    result = await db.execute(stmt)
    company_user = result.scalar_one_or_none()

    if not company_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this company"
        )

    return company_user.role


def require_role(allowed_roles: List[CompanyRoleType]):
    """
    Dependency factory to check if user has one of the allowed roles.

    Usage:
        @router.get("/staff")
        async def list_staff(
            role: CompanyRoleType = Depends(require_role([CompanyRoleType.owner, CompanyRoleType.admin]))
        ):
            ...
    """
    async def role_checker(
        user_role: CompanyRoleType = Depends(get_current_user_role)
    ) -> CompanyRoleType:
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions, contact your administrator"
            )
        return user_role

    return role_checker


async def require_owner(
    user_role: CompanyRoleType = Depends(get_current_user_role)
) -> CompanyRoleType:
    """Require owner role."""
    if user_role != CompanyRoleType.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company owners can access this resource"
        )
    return user_role


async def require_admin_or_owner(
    user_role: CompanyRoleType = Depends(get_current_user_role)
) -> CompanyRoleType:
    """Require admin or owner role."""
    if user_role not in [CompanyRoleType.owner, CompanyRoleType.admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company owners or admins can access this resource"
        )
    return user_role


async def require_staff_or_higher(
    user_role: CompanyRoleType = Depends(get_current_user_role)
) -> CompanyRoleType:
    """Require staff, admin, or owner role."""
    if user_role not in [CompanyRoleType.owner, CompanyRoleType.admin, CompanyRoleType.staff]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company staff, admins, or owners can access this resource"
        )
    return user_role
