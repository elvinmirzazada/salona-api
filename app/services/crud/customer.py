import uuid
from typing import Optional, List

from pydantic.v1 import UUID4
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Bookings
from app.models.models import (Customers, CustomerVerifications, CustomerEmails)
from app.models.enums import VerificationStatus, BookingStatus
from app.schemas.schemas import (
    CustomerCreate, CustomerUpdate, CompanyCustomer
)
from app.core.datetime_utils import utcnow


def get(db: Session, id: UUID4) -> Optional[Customers]:
    return db.query(Customers).filter(Customers.id == id).first()

def get_by_email(db: Session, email: str) -> Optional[Customers]:
    return db.query(Customers).filter(Customers.email == email).first()

def create(db: Session, *, obj_in: CustomerCreate) -> Customers:
    db_obj = Customers(**obj_in.model_dump())
    db_obj.id = str(uuid.uuid4())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def create_customer_email(db: Session, customer_id: int, email: str, status: str) -> CustomerEmails:
    db_obj = CustomerEmails(customer_id=customer_id, email=email, status=status)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update(db: Session, *, db_obj: Customers, obj_in: CustomerUpdate) -> Customers:
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    # Ensure updated_at is set to current UTC time
    db_obj.updated_at = utcnow()
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_verification_token(db: Session, token: str, type: str) -> Optional[CustomerVerifications]:
    return db.query(CustomerVerifications).filter(CustomerVerifications.token == token,
                                                  CustomerVerifications.type == type).first()

def verify_token(db: Session, db_obj: CustomerVerifications) -> bool:
    try:
        db_obj.status = VerificationStatus.VERIFIED
        db_obj.used_at = utcnow()
        
        # Update customer's email verification status
        customer = db.query(Customers).filter(Customers.id == db_obj.customer_id).first()
        if customer:
            customer.email_verified = True
            customer.updated_at = utcnow()
            db.add(customer)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return True
    except Exception:
        db.rollback()
        return False

def get_company_customers(db: Session, company_id: str) -> List[CompanyCustomer]:
    # Get all unique customers who have bookings with this company
    customers = (
        db.query(Customers)
        .join(Bookings, Customers.id == Bookings.customer_id)
        .filter(Bookings.company_id == company_id)
        .distinct()
        .all()
    )
    
    # Build the response with calculated fields
    result = []
    for customer in customers:
        # Count total bookings for this customer with this company
        total_bookings = (
            db.query(func.count(Bookings.id))
            .filter(
                Bookings.customer_id == customer.id,
                Bookings.company_id == company_id
            )
            .scalar()
        ) or 0
        
        # Calculate total spent from completed bookings only
        total_spent = (
            db.query(func.sum(Bookings.total_price))
            .filter(
                Bookings.customer_id == customer.id,
                Bookings.company_id == company_id,
                Bookings.status == BookingStatus.COMPLETED
            )
            .scalar()
        ) or 0
        
        # Get the last visit date (most recent completed booking)
        last_visit = (
            db.query(func.max(Bookings.end_at))
            .filter(
                Bookings.customer_id == customer.id,
                Bookings.company_id == company_id,
                Bookings.status == BookingStatus.COMPLETED
            )
            .scalar()
        )
        
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
        result.append(company_customer)
    
    return result
