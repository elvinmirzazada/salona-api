import uuid
from typing import Optional, List

from pydantic.v1 import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.models import Bookings
from app.models.models import (Customers, CustomerVerifications, CustomerEmails)
from app.models.enums import VerificationStatus, BookingStatus
from app.schemas.schemas import (
    CustomerCreate, CustomerUpdate, CompanyCustomer
)
from app.core.datetime_utils import utcnow


async def get(db: AsyncSession, id: UUID4) -> Optional[Customers]:
    stmt = select(Customers).filter(Customers.id == id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> Optional[Customers]:
    stmt = select(Customers).filter(Customers.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create(db: AsyncSession, *, obj_in: CustomerCreate) -> Customers:
    db_obj = Customers(**obj_in.model_dump())
    db_obj.id = str(uuid.uuid4())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def create_customer_email(db: AsyncSession, customer_id: int, email: str, status: str) -> CustomerEmails:
    db_obj = CustomerEmails(customer_id=customer_id, email=email, status=status)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update(db: AsyncSession, *, db_obj: Customers, obj_in: CustomerUpdate) -> Customers:
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    # Ensure updated_at is set to current UTC time
    db_obj.updated_at = utcnow()
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_verification_token(db: AsyncSession, token: str, type: str) -> Optional[CustomerVerifications]:
    stmt = select(CustomerVerifications).filter(
        CustomerVerifications.token == token,
        CustomerVerifications.type == type
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def verify_token(db: AsyncSession, db_obj: CustomerVerifications) -> bool:
    try:
        db_obj.status = VerificationStatus.VERIFIED
        db_obj.used_at = utcnow()
        
        # Update customer's email verification status
        stmt = select(Customers).filter(Customers.id == db_obj.customer_id)
        result = await db.execute(stmt)
        customer = result.scalar_one_or_none()

        if customer:
            customer.email_verified = True
            customer.updated_at = utcnow()
            db.add(customer)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return True
    except Exception:
        await db.rollback()
        return False


async def get_company_customers(db: AsyncSession, company_id: str) -> List[CompanyCustomer]:
    # Get all unique customers who have bookings with this company
    stmt = (select(Customers)
            .join(Bookings, Customers.id == Bookings.customer_id)
            .filter(Bookings.company_id == company_id)
            .distinct())
    result = await db.execute(stmt)
    customers = result.scalars().all()

    # Build the response with calculated fields
    result_list = []
    for customer in customers:
        # Count total bookings for this customer with this company
        stmt_count = select(func.count(Bookings.id)).filter(
            Bookings.customer_id == customer.id,
            Bookings.company_id == company_id
        )
        count_result = await db.execute(stmt_count)
        total_bookings = count_result.scalar() or 0

        # Calculate total spent from completed bookings only
        stmt_sum = select(func.sum(Bookings.total_price)).filter(
            Bookings.customer_id == customer.id,
            Bookings.company_id == company_id,
            Bookings.status == BookingStatus.COMPLETED
        )
        sum_result = await db.execute(stmt_sum)
        total_spent = sum_result.scalar() or 0

        # Get the last visit date (most recent completed booking)
        stmt_max = select(func.max(Bookings.end_at)).filter(
            Bookings.customer_id == customer.id,
            Bookings.company_id == company_id,
            Bookings.status == BookingStatus.COMPLETED
        )
        max_result = await db.execute(stmt_max)
        last_visit = max_result.scalar()

        # Create CompanyCustomer schema with calculated fields
        company_customer = CompanyCustomer(
            id=customer.id,
            first_name=customer.first_name,
            last_name=customer.last_name,
            email=customer.email,
            phone=customer.phone,
            status=customer.status,
            email_verified=customer.email_verified,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            total_bookings=total_bookings,
            total_spent=total_spent,
            last_visit=last_visit
        )
        result_list.append(company_customer)

    return result_list

