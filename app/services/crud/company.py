import uuid
from typing import Optional

from pydantic.v1 import UUID4
from sqlalchemy.orm import Session

from app.models import CompanyRoleType, StatusType
from app.models.models import (CompanyUsers, Companies)
from app.schemas.schemas import (
    CompanyCreate,
    User
)


def get(db: Session, id: UUID4) -> Optional[Companies]:
    return db.query(Companies).filter(Companies.id == id).first()


def create(db: Session, *, obj_in: CompanyCreate, current_user: User) -> Companies:
    try:
        db_obj = Companies(**obj_in.model_dump())
        db_obj.id = str(uuid.uuid4())
        db.add(db_obj)
        print(db_obj.id)

        cmp_usr_obj = CompanyUsers(user_id=current_user.id,
                                   company_id=db_obj.id,
                                   role=CompanyRoleType.admin,
                                   status=StatusType.active)
        cmp_usr_obj.id = str(uuid.uuid4())
        db.add(cmp_usr_obj)
        db.commit()
        db.refresh(cmp_usr_obj)
        db.refresh(db_obj)

        return db_obj
    except Exception as e:
        db.rollback()
        raise e

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