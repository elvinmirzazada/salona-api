import uuid
from typing import Optional, List

from pydantic.v1 import UUID4
from sqlalchemy.orm import Session

from app.models.models import (Users)
from app.schemas.schemas import (
    UserCreate
)


def get(db: Session, id: UUID4) -> Optional[Users]:
    return db.query(Users).filter(Users.id == id).first()


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
#
# def update(self, db: Session, *, db_obj: Professional, obj_in: ProfessionalUpdate) -> Professional:
#     update_data = obj_in.model_dump(exclude_unset=True)
#     for field, value in update_data.items():
#         setattr(db_obj, field, value)
#     db.add(db_obj)
#     db.commit()
#     db.refresh(db_obj)
#     return db_obj
