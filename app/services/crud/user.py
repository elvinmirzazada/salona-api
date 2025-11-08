import uuid
from typing import Optional, List
from datetime import datetime

from pydantic.v1 import UUID4
from sqlalchemy.orm import Session

from app.models import CompanyUsers, CustomerStatusType
from app.models.models import Users, UserVerifications
from app.models.enums import VerificationStatus
from app.schemas import CompanyUser, User
from app.schemas.schemas import (
    UserCreate
)


def get(db: Session, id: UUID4) -> Optional[Users]:
    return db.query(Users, CompanyUsers.company_id).outerjoin(CompanyUsers, CompanyUsers.user_id == Users.id).filter(Users.id == id).first()


def get_all(db: Session) -> List[Users]:
    return db.query(Users).all()


def get_by_email(db: Session, email: str) -> Optional[Users]:
    return db.query(Users).filter(Users.email == email).first()


def create(db: Session, *, obj_in: UserCreate) -> Users:
    db_obj = Users(**obj_in.model_dump())
    db_obj.id = str(uuid.uuid4())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_verification_token(db: Session, token: str, type: str) -> Optional[UserVerifications]:
    """Get verification token by token string and type"""
    return db.query(UserVerifications).filter(
        UserVerifications.token == token,
        UserVerifications.type == type
    ).first()


def verify_token(db: Session, db_obj: UserVerifications) -> bool:
    """Mark verification token as verified and update user email_verified status"""
    try:
        db_obj.status = VerificationStatus.VERIFIED
        db_obj.used_at = datetime.now()

        # Update user's email_verified status
        user = db.query(Users).filter(Users.id == db_obj.user_id).first()
        if user:
            user.email_verified = True
            user.status = CustomerStatusType.active
            db.add(user)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return True
    except Exception as e:
        db.rollback()
        print(f"Error verifying token: {str(e)}")
        return False


def get_company_users(db: Session, company_id: str) -> List[CompanyUser]:
    """
    Get all users for a company
    """
    users = db.query(CompanyUsers).join(Users, Users.id == CompanyUsers.user_id).filter(
        Users.status == 'active', CompanyUsers.company_id == company_id, CompanyUsers.status == 'active'
    ).all()
    # result = []
    # for company_user, user in users:
    #     result.append(CompanyUser(
    #         user_id=company_user.user_id,
    #         company_id=company_user.company_id,
    #         role=company_user.role,
    #         status=company_user.status,
    #         user=User(
    #             id=user.id,
    #             first_name=user.first_name,
    #             last_name=user.last_name,
    #             email=user.email,
    #             phone=user.phone,
    #             status=user.status,
    #             created_at=user.created_at,
    #             updated_at=user.updated_at
    #         )
    #     ))
    return users


def get_company_by_user(db: Session, user_id: str) -> Optional[CompanyUsers]:
    return db.query(CompanyUsers).filter(
        CompanyUsers.user_id == user_id).first()