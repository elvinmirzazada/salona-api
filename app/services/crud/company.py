import uuid
from typing import Optional, List
from datetime import date
from pydantic.v1 import UUID4
from sqlalchemy.orm import Session

from app.models import CompanyRoleType, StatusType, UserAvailabilities, UserTimeOffs, CategoryServices, \
    CompanyCategories, CompanyEmails, CompanyPhones, Users
from app.models.models import CompanyUsers, Companies
from app.schemas import CompanyEmailCreate, CompanyEmail, CompanyEmailBase, CompanyPhoneCreate, UserCreate, CompanyUser
from app.schemas.schemas import (
    CompanyCreate,
    User
)
from app.services.auth import hash_password


def get(db: Session, id: str) -> Optional[Companies]:
    return db.query(Companies).filter(Companies.id == id).first()


def get_company_users(db: Session, company_id: str) -> List[CompanyUsers]:
    """Get all users belonging to the given company."""
    return list(db.query(CompanyUsers).filter(CompanyUsers.company_id == company_id).all())


def get_company_user(db: Session, company_id: str, user_id: str) -> Optional[CompanyUser]:
    """Get company user with user details."""
    company_user = (db.query(CompanyUsers)
                    .join(Users, Users.id == CompanyUsers.user_id)
                    .filter(CompanyUsers.company_id == company_id, CompanyUsers.user_id == user_id)
                    .first())
    
    if not company_user:
        return None
    
    # Convert SQLAlchemy model to Pydantic schema
    return CompanyUser.model_validate(company_user)


def get_company_services(db: Session, company_id: str) -> List[CompanyCategories]:
    """Get all services belonging to the given company."""
    return list(db.query(CompanyCategories).join(CategoryServices, CategoryServices.category_id==CompanyCategories.id)
                .filter(CompanyCategories.company_id == company_id).all())


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
    db.commit()
    db.refresh(db_obj)

    cmp_usr_obj = CompanyUsers(user_id=current_user.id,
                               company_id=db_obj.id,
                               role=CompanyRoleType.admin,
                               status=StatusType.active)
    db.add(cmp_usr_obj)
    db.commit()
    db.refresh(db_obj)

    return db_obj


def update(db: Session, *, db_obj: Companies, obj_in: dict) -> Companies:
    """
    Update company information

    Args:
        db: Database session
        db_obj: Existing company object to update
        obj_in: Data to update the company with

    Returns:
        Updated company object
    """
    for field, value in obj_in.items():
        if value is not None:
            setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def create_company_email(db: Session, *, obj_in: CompanyEmailCreate):
    """
    Create new emails for a company, handling duplicate emails

    Args:
        db: Database session
        obj_in: Data with company emails to add

    Returns:
        List of created/updated email objects
    """
    # Get existing emails for this company to check duplicates
    existing_emails = db.query(CompanyEmails).filter(
        CompanyEmails.company_id == obj_in.company_id
    ).all()

    # Create a set of existing email addresses for efficient lookup
    existing_email_set = {str(email.email).lower() for email in existing_emails}

    for email in obj_in.emails:
        # Check if this email already exists for this company
        if str(email.email).lower() in existing_email_set:
            # Skip this email as it already exists
            continue

        # Create new email record
        db_obj = CompanyEmails(
            company_id=obj_in.company_id,
            email=str(email.email).lower(),
            status=email.status.lower()
        )
        db_obj.id = str(uuid.uuid4())
        db.add(db_obj)

    # Commit all new emails at once
    db.commit()


def get_company_emails(db: Session, company_id: str) -> List[CompanyEmails]:
    """
    Get all emails for a specific company
    """
    company_emails = db.query(CompanyEmails).filter(CompanyEmails.company_id == company_id).all()

    return company_emails



def get_company_email(db: Session, email_id: str) -> Optional[CompanyEmails]:
    """
    Get a specific company email by ID
    """
    return db.query(CompanyEmails).filter(CompanyEmails.id == email_id).first()


def delete_company_email(db: Session, email_id: str, company_id: str) -> bool:
    """
    Delete a company email
    """
    db_obj = db.query(CompanyEmails).filter(
        CompanyEmails.id == email_id,
        CompanyEmails.company_id == company_id
    ).first()

    if not db_obj:
        return False

    db.delete(db_obj)
    db.commit()
    return True


def create_company_phone(db: Session, *, obj_in: CompanyPhoneCreate) -> List[CompanyPhones]:
    """
    Create new phone numbers for a company, handling duplicate phone numbers

    Args:
        db: Database session
        obj_in: Data with company phone numbers to add

    Returns:
        List of created phone number objects
    """
    # Get existing phone numbers for this company to check duplicates
    existing_phones = db.query(CompanyPhones).filter(
        CompanyPhones.company_id == obj_in.company_id
    ).all()

    # Create a set of existing phone numbers for efficient lookup
    existing_phone_set = {phone.phone for phone in existing_phones}

    created_phones = []
    for phone_data in obj_in.company_phones:
        # Check if this phone number already exists for this company
        if phone_data.phone in existing_phone_set:
            # Skip this phone number as it already exists
            continue

        # Create new phone number record
        db_obj = CompanyPhones(
            company_id=obj_in.company_id,
            phone=phone_data.phone,
            is_primary=phone_data.is_primary,
            status=phone_data.status
        )
        # db_obj.id = str(uuid.uuid4())
        
        db.add(db_obj)
        created_phones.append(db_obj)
        
    # Commit all new phone numbers at once
    db.commit()

    # Refresh all newly created objects
    for phone in created_phones:
        db.refresh(phone)

    return created_phones


def get_company_phones(db: Session, company_id: str) -> List[CompanyPhones]:
    """
    Get all phone numbers for a specific company
    """
    return db.query(CompanyPhones).filter(CompanyPhones.company_id == company_id).all()


def get_company_phone(db: Session, phone_id: str) -> Optional[CompanyPhones]:
    """
    Get a specific company phone by ID
    """
    return db.query(CompanyPhones).filter(CompanyPhones.id == phone_id).first()


def delete_company_phone(db: Session, phone_id: str, company_id: str) -> bool:
    """
    Delete a company phone number
    """
    db_obj = db.query(CompanyPhones).filter(
        CompanyPhones.id == phone_id,
        CompanyPhones.company_id == company_id
    ).first()
    
    if not db_obj:
        return False

    db.delete(db_obj)
    db.commit()
    return True


def create_company_member(db: Session, *, user_in: UserCreate, company_id: str, role: CompanyRoleType) -> CompanyUsers:
    """
    Create a new user and add them to a company with the specified role.

    Args:
        db: Database session
        user_in: User creation data
        company_id: Company ID to add the user to
        role: Role to assign to the user in the company

    Returns:
        CompanyUsers object with the user relationship
    """
    # Check if user with this email already exists
    existing_user = db.query(Users).filter(Users.email == user_in.email).first()

    if existing_user:
        # Check if user is already part of this company
        existing_company_user = db.query(CompanyUsers).filter(
            CompanyUsers.user_id == existing_user.id,
            CompanyUsers.company_id == company_id
        ).first()

        if existing_company_user:
            raise ValueError("User is already a member of this company")

        # Add existing user to the company
        company_user = CompanyUsers(
            user_id=existing_user.id,
            company_id=company_id,
            role=role,
            status=StatusType.active
        )
        db.add(company_user)
        db.commit()
        db.refresh(company_user)
        return company_user

    # Create new user
    user_data = user_in.model_dump()
    user_data['password'] = hash_password(user_data['password'])

    new_user = Users(**user_data)
    new_user.id = str(uuid.uuid4())
    new_user.status = StatusType.active

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Add user to company
    company_user = CompanyUsers(
        user_id=new_user.id,
        company_id=company_id,
        role=role,
        status=StatusType.active
    )
    db.add(company_user)
    db.commit()
    db.refresh(company_user)

    return company_user
