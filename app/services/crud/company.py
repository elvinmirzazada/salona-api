import uuid
from typing import Optional, List
from datetime import date
from pydantic.v1 import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.models import CompanyRoleType, StatusType, UserAvailabilities, UserTimeOffs, CategoryServices, \
    CompanyCategories, CompanyEmails, CompanyPhones, Users
from app.models.models import CompanyUsers, Companies
from app.schemas import CompanyEmailCreate, CompanyEmail, CompanyEmailBase, CompanyPhoneCreate, UserCreate, CompanyUser, \
    CompanyUserUpdate, CompanyUpdate
from app.schemas.schemas import (
    CompanyCreate,
    User
)
from app.services.auth import hash_password
from app.core.datetime_utils import utcnow


async def get(db: AsyncSession, id: str) -> Optional[Companies]:
    stmt = select(Companies).filter(Companies.id == id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_slug(db: AsyncSession, slug: str) -> Optional[Companies]:
    stmt = select(Companies).filter(Companies.slug == slug)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_company_users(db: AsyncSession, company_id: str) -> List[CompanyUsers]:
    """Get all users belonging to the given company."""
    stmt = (select(CompanyUsers)
            .options(selectinload(CompanyUsers.user))  # Eager load user details
            .filter(CompanyUsers.company_id == company_id))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_company_user(db: AsyncSession, company_id: str, user_id: str) -> Optional[CompanyUser]:
    """Get company user with user details."""
    stmt = (select(CompanyUsers)
            .options(selectinload(CompanyUsers.user))  # Eager load user details
            .join(Users, Users.id == CompanyUsers.user_id)
            .filter(CompanyUsers.company_id == company_id, CompanyUsers.user_id == user_id))
    result = await db.execute(stmt)
    company_user = result.scalar_one_or_none()

    if not company_user:
        return None
    
    # Convert SQLAlchemy model to Pydantic schema
    return CompanyUser.model_validate(company_user)


async def get_company_services(db: AsyncSession, company_id: str) -> List[CompanyCategories]:
    """Get all services belonging to the given company."""
    stmt = (select(CompanyCategories)
            .join(CategoryServices, CategoryServices.category_id == CompanyCategories.id)
            .filter(CompanyCategories.company_id == company_id))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_company_all_users_availabilities(db: AsyncSession, company_id: str) -> List:
    """Get all availabilities for users belonging to the given company."""
    stmt = (select(UserAvailabilities)
            .join(CompanyUsers, UserAvailabilities.user_id == CompanyUsers.user_id)
            .filter(CompanyUsers.company_id == company_id, UserAvailabilities.is_available == True))
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_company_user_availabilities(db: AsyncSession, user_id: str, company_id: str) -> List:
    """Get all availabilities for users belonging to the given company."""
    stmt = (select(UserAvailabilities)
            .join(CompanyUsers, UserAvailabilities.user_id == CompanyUsers.user_id)
            .filter(CompanyUsers.company_id == company_id,
                    CompanyUsers.user_id == user_id,
                    UserAvailabilities.is_available == True))
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_company_all_users_time_offs(db: AsyncSession, company_id: str, start_date: date, end_date: date) -> List:
    """Get all time-offs within a date range"""
    stmt = (select(UserTimeOffs, CompanyUsers.user_id)
            .join(CompanyUsers, UserTimeOffs.user_id == CompanyUsers.user_id)
            .filter(CompanyUsers.company_id == company_id,
                    UserTimeOffs.start_date <= end_date,
                    UserTimeOffs.end_date >= start_date))
    result = await db.execute(stmt)
    return result.all()


async def get_company_user_time_offs(db: AsyncSession, user_id: str, company_id: str, start_date: date, end_date: date) -> List:
    """Get all time-offs within a date range"""
    stmt = (select(UserTimeOffs, CompanyUsers.user_id)
            .join(CompanyUsers, UserTimeOffs.user_id == CompanyUsers.user_id)
            .filter(CompanyUsers.company_id == company_id,
                    CompanyUsers.user_id == user_id,
                    UserTimeOffs.start_date <= end_date,
                    UserTimeOffs.end_date >= start_date))
    result = await db.execute(stmt)
    return result.all()


async def create(db: AsyncSession, *, obj_in: CompanyCreate, current_user: User) -> Companies:

    db_obj = Companies(**obj_in.model_dump())
    # db_obj.id = str(uuid.uuid4())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)

    cmp_usr_obj = CompanyUsers(user_id=current_user.id,
                               company_id=db_obj.id,
                               role=CompanyRoleType.admin,
                               status=StatusType.active)
    db.add(cmp_usr_obj)
    await db.commit()
    await db.refresh(db_obj)

    return db_obj


async def update(db: AsyncSession, *, db_obj: Companies, obj_in: CompanyUpdate) -> Companies:
    """
    Update company information

    Args:
        db: Database session
        db_obj: Existing company object to update
        obj_in: Data to update the company with

    Returns:
        Updated company object
    """
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    # Ensure updated_at is set to current UTC time
    db_obj.updated_at = utcnow()
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def create_company_email(db: AsyncSession, *, obj_in: CompanyEmailCreate):
    """
    Create new emails for a company, handling duplicate emails

    Args:
        db: Database session
        obj_in: Data with company emails to add

    Returns:
        List of created/updated email objects
    """
    # Get existing emails for this company to check duplicates
    stmt = select(CompanyEmails).filter(CompanyEmails.company_id == obj_in.company_id)
    result = await db.execute(stmt)
    existing_emails = result.scalars().all()

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
    await db.commit()


async def get_company_emails(db: AsyncSession, company_id: str) -> List[CompanyEmails]:
    """
    Get all emails for a specific company
    """
    stmt = select(CompanyEmails).filter(CompanyEmails.company_id == company_id)
    result = await db.execute(stmt)
    company_emails = result.scalars().all()

    return company_emails


async def get_company_email(db: AsyncSession, email_id: str) -> Optional[CompanyEmails]:
    """
    Get a specific company email by ID
    """
    stmt = select(CompanyEmails).filter(CompanyEmails.id == email_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_company_email(db: AsyncSession, email_id: str, company_id: str) -> bool:
    """
    Delete a company email
    """
    stmt = select(CompanyEmails).filter(
        CompanyEmails.id == email_id,
        CompanyEmails.company_id == company_id
    )
    result = await db.execute(stmt)
    db_obj = result.scalar_one_or_none()

    if not db_obj:
        return False

    await db.delete(db_obj)
    await db.commit()
    return True


async def create_company_phone(db: AsyncSession, *, obj_in: CompanyPhoneCreate) -> List[CompanyPhones]:
    """
    Create new phone numbers for a company, handling duplicate phone numbers

    Args:
        db: Database session
        obj_in: Data with company phone numbers to add

    Returns:
        List of created phone number objects
    """
    # Get existing phone numbers for this company to check duplicates
    stmt = select(CompanyPhones).filter(CompanyPhones.company_id == obj_in.company_id)
    result = await db.execute(stmt)
    existing_phones = result.scalars().all()

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
    await db.commit()

    # Refresh all newly created objects
    for phone in created_phones:
        await db.refresh(phone)

    return created_phones


async def get_company_phones(db: AsyncSession, company_id: str) -> List[CompanyPhones]:
    """
    Get all phone numbers for a specific company
    """
    stmt = select(CompanyPhones).filter(CompanyPhones.company_id == company_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_company_phone(db: AsyncSession, phone_id: str) -> Optional[CompanyPhones]:
    """
    Get a specific company phone by ID
    """
    stmt = select(CompanyPhones).filter(CompanyPhones.id == phone_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_company_phone(db: AsyncSession, phone_id: str, company_id: str) -> bool:
    """
    Delete a company phone number
    """
    stmt = select(CompanyPhones).filter(
        CompanyPhones.id == phone_id,
        CompanyPhones.company_id == company_id
    )
    result = await db.execute(stmt)
    db_obj = result.scalar_one_or_none()

    if not db_obj:
        return False

    await db.delete(db_obj)
    await db.commit()
    return True


async def create_company_member(db: AsyncSession, *, user_in: UserCreate, company_id: str, role: CompanyRoleType) -> CompanyUsers:
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
    from app.services.crud import user_availability as crud_user_availability

    # Check if user with this email already exists
    stmt = select(Users).filter(Users.email == user_in.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Check if user is already part of this company
        stmt = select(CompanyUsers).filter(
            CompanyUsers.user_id == existing_user.id,
            CompanyUsers.company_id == company_id
        )
        result = await db.execute(stmt)
        existing_company_user = result.scalar_one_or_none()

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
        await db.commit()
        await db.refresh(company_user)

        # Handle availabilities for existing user
        if user_in.availabilities:
            await crud_user_availability.update_user_availabilities(db, str(existing_user.id), user_in.availabilities)

        return company_user

    # Create new user
    user_data = user_in.model_dump(exclude={'availabilities'})
    user_data['password'] = hash_password(user_data['password'])

    new_user = Users(**user_data)
    new_user.id = str(uuid.uuid4())
    new_user.status = StatusType.active

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Add user to company
    company_user = CompanyUsers(
        user_id=new_user.id,
        company_id=company_id,
        role=role,
        status=StatusType.active
    )
    db.add(company_user)
    await db.commit()
    await db.refresh(company_user)

    # Handle availabilities for new user
    if user_in.availabilities:
        await crud_user_availability.bulk_create_user_availabilities(db, str(new_user.id), user_in.availabilities)

    return company_user


async def update_company_user(db: AsyncSession, *, company_id: str, user_id: str, obj_in: CompanyUserUpdate) -> Optional[CompanyUsers]:
    """
    Update a company user's role, status, user profile fields, and availabilities.

    Args:
        db: Database session
        company_id: Company ID
        user_id: User ID to update
        obj_in: Data to update (role, status, user fields, availabilities)

    Returns:
        Updated CompanyUsers object or None if not found
    """
    from app.services.crud import user_availability as crud_user_availability

    stmt = (select(CompanyUsers)
        .options(selectinload(CompanyUsers.user))  # Eager load user details
        .filter(
        CompanyUsers.company_id == company_id,
        CompanyUsers.user_id == user_id
    ))
    result = await db.execute(stmt)
    company_user = result.scalar_one_or_none()

    if not company_user:
        return None

    # Extract availabilities before converting to dict
    availabilities = obj_in.availabilities

    # Convert to dict, excluding availabilities and unset fields
    update_data = obj_in.model_dump(exclude_unset=True, exclude={'availabilities'})

    # Separate company_user fields from user fields
    company_user_fields = {'role', 'status'}
    user_fields = {'first_name', 'last_name', 'phone', 'languages', 'position', 'profile_photo_url'}

    # Update CompanyUsers fields
    for field, value in update_data.items():
        if field in company_user_fields and hasattr(company_user, field):
            setattr(company_user, field, value)

    # Update User fields
    user_updates = {field: value for field, value in update_data.items() if field in user_fields}
    if user_updates:
        stmt = select(Users).filter(Users.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            for field, value in user_updates.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            user.updated_at = utcnow()
            db.add(user)

    # Update timestamp
    company_user.updated_at = utcnow()

    db.add(company_user)
    await db.commit()
    await db.refresh(company_user)

    # Handle availabilities update - only if explicitly provided (not None)
    # If availabilities is None, it means it wasn't sent in the request
    # If availabilities is [], it means explicitly clearing all availabilities
    # If availabilities has items, it means updating with new availabilities
    if availabilities is not None:
        stmt = delete(UserAvailabilities).filter(UserAvailabilities.user_id == user_id)
        await db.execute(stmt)

        db_availabilities = []
        for availability_in in availabilities:
            db_availability = UserAvailabilities(
                id=str(uuid.uuid4()),
                user_id=user_id,
                day_of_week=availability_in.day_of_week,
                start_time=availability_in.start_time,
                end_time=availability_in.end_time,
                is_available=availability_in.is_available,
                created_at=utcnow(),
                updated_at=utcnow()
            )
            db_availabilities.append(db_availability)

        db.add_all(db_availabilities)
        await db.commit()
    return company_user


async def delete_company_user(db: AsyncSession, *, company_id: str, user_id: str) -> bool:
    """
    Remove a user from a company (soft delete by setting status to inactive).

    Args:
        db: Database session
        company_id: Company ID
        user_id: User ID to remove

    Returns:
        True if user was removed, False if not found
    """
    stmt = select(CompanyUsers).filter(
        CompanyUsers.company_id == company_id,
        CompanyUsers.user_id == user_id
    )
    result = await db.execute(stmt)
    company_user = result.scalar_one_or_none()

    if not company_user:
        return False

    # Soft delete by setting status to inactive
    company_user.status = StatusType.inactive
    company_user.updated_at = utcnow()

    db.add(company_user)
    await db.commit()

    return True
