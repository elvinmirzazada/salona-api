import uuid
from typing import Optional, List
from datetime import date
from pydantic.v1 import UUID4
from sqlalchemy.orm import Session

from app.models import CompanyRoleType, StatusType, UserAvailabilities, UserTimeOffs
from app.models.models import CompanyUsers, Companies
from app.schemas.schemas import (
    CompanyCreate,
    User
)


def get(db: Session, id: UUID4) -> Optional[Companies]:
    return db.query(Companies).filter(Companies.id == id).first()


def get_company_users(db: Session, company_id: str) -> List[CompanyUsers]:
    """Get all users belonging to the given company."""
    return list(db.query(CompanyUsers).filter(CompanyUsers.company_id == company_id).all())


def get_company_all_users_availabilities(db: Session, company_id: str) -> List:
    """Get all availabilities for users belonging to the given company."""
    return (db.query(UserAvailabilities)
     .join(CompanyUsers, UserAvailabilities.user_id == CompanyUsers.user_id).filter(
        CompanyUsers.company_id == company_id,
        UserAvailabilities.is_available == True
    ).all())


def get_company_user_availabilities(db: Session, user_id: str, company_id: str) -> List:
    """Get all availabilities for users belonging to the given company."""
    return (db.query(UserAvailabilities)
     .join(CompanyUsers, UserAvailabilities.user_id == CompanyUsers.user_id).filter(
        CompanyUsers.company_id == company_id,
        CompanyUsers.user_id == user_id,
        UserAvailabilities.is_available == True
    ).all())


def get_company_all_users_time_offs(db: Session, company_id: str, start_date: date, end_date: date) -> List:
    """Get all time-offs within a date range"""
    return (db.query(UserTimeOffs, CompanyUsers.user_id)
     .join(CompanyUsers, UserTimeOffs.user_id == CompanyUsers.user_id).filter(
        CompanyUsers.company_id == company_id,
        UserTimeOffs.start_date <= end_date,
        UserTimeOffs.end_date >= start_date
    ).all())


def get_company_user_time_offs(db: Session, user_id: str, company_id: str, start_date: date, end_date: date) -> List:
    """Get all time-offs within a date range"""
    return (db.query(UserTimeOffs, CompanyUsers.user_id)
     .join(CompanyUsers, UserTimeOffs.user_id == CompanyUsers.user_id).filter(
        CompanyUsers.company_id == company_id,
        CompanyUsers.user_id == user_id,
        UserTimeOffs.start_date <= end_date,
        UserTimeOffs.end_date >= start_date
    ).all())


def create(db: Session, *, obj_in: CompanyCreate, current_user: User) -> Companies:

    db_obj = Companies(**obj_in.model_dump())
    # db_obj.id = str(uuid.uuid4())
    db.add(db_obj)

    cmp_usr_obj = CompanyUsers(user_id=current_user.id,
                               company_id=db_obj.id,
                               role=CompanyRoleType.admin,
                               status=StatusType.active)
    db.add(cmp_usr_obj)
    db.commit()
    db.refresh(db_obj)

    return db_obj

#
#     def update(self, db: Session, *, db_obj: Business, obj_in: BusinessUpdate) -> Business:
#         update_data = obj_in.model_dump(exclude_unset=True)
#         for field, value in update_data.items():
#             setattr(db_obj, field, value)
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj
#
#