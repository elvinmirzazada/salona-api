import uuid
from typing import Optional, List
from datetime import datetime

from pydantic.v1 import UUID4
from sqlalchemy.orm import Session

from app.models import Companies, Bookings
from app.models.models import (Customers, CustomerVerifications, CustomerEmails)
from app.models.enums import VerificationStatus
from app.schemas import CompanyCustomers
from app.schemas.schemas import (
    CustomerCreate, CustomerUpdate
)


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
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_verification_token(db: Session, token: str, type: str) -> Optional[CustomerVerifications]:
    return db.query(CustomerVerifications).filter(CustomerVerifications.token == token,
                                                  CustomerVerifications.type == type).first()

def verify_token(db: Session, db_obj: CustomerVerifications) -> bool:
    """Mark verification token as verified and update customer email_verified status"""
    try:
        db_obj.status = VerificationStatus.VERIFIED
        db_obj.used_at = datetime.now()

        # Update customer's email_verified status
        customer = db.query(Customers).filter(Customers.id == db_obj.customer_id).first()
        if customer:
            customer.email_verified = True
            db.add(customer)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return True
    except Exception as e:
        db.rollback()
        print(f"Error verifying token: {str(e)}")
        return False


def get_company_customers(db: Session, company_id: str) -> List[Customers]:
    """Get all customers belonging to the given company."""
    return list(db.query(Customers).join(Bookings, Customers.id==Bookings.customer_id)
                .filter(Bookings.company_id == company_id).all())
