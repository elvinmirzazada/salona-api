import uuid
from typing import Optional

from pydantic.v1 import UUID4
from sqlalchemy.orm import Session

from app.models.models import (Customers, CustomerVerifications, CustomerEmails)
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

def verify_token(db: Session, db_obj: CustomerVerifications) -> CustomerVerifications:
    db_obj.status = "verified"
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

