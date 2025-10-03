from typing import List, Optional, Any
from datetime import date, datetime
import uuid

from sqlalchemy.orm import Session
from pydantic.v1 import UUID4

from app.models import CompanyUsers
from app.models.models import UserTimeOffs
from app.schemas.schemas import TimeOffCreate, TimeOffUpdate


def get_user_time_offs(
    db: Session,
    company_id: str,
    start_date: datetime = None,
    end_date: datetime = None
) -> List[UserTimeOffs]:
    """
    Get all time-offs for a user with optional date filtering
    """
    query = (db.query(UserTimeOffs).join(CompanyUsers, CompanyUsers.user_id == UserTimeOffs.user_id)
             .filter(CompanyUsers.company_id == company_id))
    
    if start_date and end_date:
        # Get time offs that overlap with the given date range
        query = query.filter(
            UserTimeOffs.start_date <= end_date,
            UserTimeOffs.end_date >= start_date
        )
    
    return list(query.all())


def get(db: Session, time_off_id: UUID4) -> Optional[UserTimeOffs]:
    """
    Get a specific time off by ID
    """
    return db.query(UserTimeOffs).filter(UserTimeOffs.id == time_off_id).first()


def create(db: Session, *, obj_in: TimeOffCreate, company_id: Optional[str]) -> UserTimeOffs:
    """
    Create a new time off period for a user

    If company_id is provided, validates that the user belongs to that company
    """
    # Validate that end_date is not before start_date
    if obj_in.end_date < obj_in.start_date:
        raise ValueError("End date cannot be before start date")
    
    # Check if company_id is provided, validate user belongs to this company
    if company_id:
        company_user = db.query(CompanyUsers).filter(
            CompanyUsers.user_id == obj_in.user_id,
            CompanyUsers.company_id == company_id
        ).first()

        if not company_user:
            raise ValueError(f"User {obj_in.user_id} does not belong to company {obj_in.company_id}")

    db_obj = UserTimeOffs(
        # id=uuid.uuid4(),
        user_id=obj_in.user_id,
        start_date=obj_in.start_date,
        end_date=obj_in.end_date,
        reason=obj_in.reason
    )
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update(db: Session, *, db_obj: UserTimeOffs, obj_in: TimeOffUpdate) -> UserTimeOffs:
    """
    Update an existing time off period
    """
    # Update fields if provided
    if obj_in.start_date is not None:
        db_obj.start_date = obj_in.start_date
    
    if obj_in.end_date is not None:
        db_obj.end_date = obj_in.end_date
    
    if obj_in.reason is not None:
        db_obj.reason = obj_in.reason
    
    # Validate that end_date is not before start_date after updates
    if db_obj.end_date < db_obj.start_date:
        raise ValueError("End date cannot be before start date")
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete(db: Session, *, time_off_id: UUID4) -> bool:
    """
    Delete a time off period
    """
    db_obj = db.query(UserTimeOffs).filter(UserTimeOffs.id == time_off_id).first()
    if not db_obj:
        return False
    
    db.delete(db_obj)
    db.commit()
    return True


def check_overlapping_time_offs(
    db: Session, 
    user_id: UUID4, 
    start_date: datetime,
    end_date: datetime,
    exclude_id: UUID4 = None
) -> bool:
    """
    Check if a new time off period overlaps with existing ones
    Returns True if there are overlaps, False otherwise
    """
    query = db.query(UserTimeOffs).filter(
        UserTimeOffs.user_id == user_id,
        UserTimeOffs.start_date <= end_date,
        UserTimeOffs.end_date >= start_date
    )

    # Exclude the current time off if updating
    if exclude_id:
        query = query.filter(UserTimeOffs.id != exclude_id)

    return query.count() > 0


# def get_company_user_time_offs(
#         db: Session,
#         company_id: str,
#         start_date: date = None,
#         end_date: date = None
# ) -> List[UserTimeOffs]:
#     """
#     Get all time-offs for a user with optional date filtering
#     """
    # query = (db.query(UserTimeOffs).join(CompanyUsers, CompanyUsers.user_id == UserTimeOffs.user_id)
    #          .filter(UserTimeOffs.user_id == user_id,
    #                  CompanyUsers.company_id == company_id))
    #
    # if start_date and end_date:
    #     # Get time offs that overlap with the given date range
    #     query = query.filter(
    #         UserTimeOffs.start_date <= end_date,
    #         UserTimeOffs.end_date >= start_date
    #     )
    #
    # return list(query.all())
