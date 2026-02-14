from typing import Optional, Dict, List
from collections import defaultdict
from pydantic.v1 import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from app.models.models import CategoryServices, CompanyCategories, ServiceStaff, Users
from app.schemas import CategoryServiceResponse, CompanyCategoryCreate, CompanyCategoryUpdate, CategoryServiceCreate, \
    CategoryServiceUpdate, StaffMember
from app.schemas.schemas import CompanyCategoryWithServicesResponse



#
#     def get_multi_by_business(self, db: Session, business_id: int, skip: int = 0, limit: int = 100) -> List[Service]:
#         return db.query(Service).filter(Service.business_id == business_id).offset(skip).limit(limit).all()
#
#     def create(self, db: Session, *, obj_in: ServiceCreate) -> Service:
#         db_obj = Service(**obj_in.model_dump())
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj
#
#     def update(self, db: Session, *, db_obj: Service, obj_in: ServiceUpdate) -> Service:
#         update_data = obj_in.model_dump(exclude_unset=True)
#         for field, value in update_data.items():
#             setattr(db_obj, field, value)
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj


async def get_service(db: AsyncSession, service_id: str, company_id: str) -> Optional[CategoryServices]:
    """
    Get all services for a company grouped by category
    Returns a dictionary where keys are categories and values are lists of services
    """
    stmt = (select(CategoryServices)
            .options(selectinload(CategoryServices.service_staff))
            .options(selectinload(CategoryServices.company_category))
            .join(CompanyCategories, CategoryServices.category_id == CompanyCategories.id)
            .filter(CompanyCategories.company_id == company_id, CategoryServices.id == service_id))

    result = await db.execute(stmt)
    service = result.scalar_one_or_none()

    return service


async def get_company_services(db: AsyncSession, company_id: str) -> List[CompanyCategoryWithServicesResponse]:
    """
    Get all services for a company grouped by category with assigned staff in hierarchical structure
    Returns categories with their services and subcategories
    """
    # Get all categories and services for the company
    stmt = (select(CompanyCategories)
            .options(selectinload(CompanyCategories.category_service))
            .filter(CompanyCategories.company_id == company_id))
    result = await db.execute(stmt)
    all_categories = result.scalars().all()

    # Build a dictionary for quick lookup
    category_dict = {}
    for cat in all_categories:
        category_dict[str(cat.id)] = {
            'category': cat,
            'services': [],
            'subcategories': []
        }

    # Get all services for the company
    stmt = (select(CategoryServices, CompanyCategories)
            .join(CompanyCategories, CategoryServices.category_id == CompanyCategories.id)
            .filter(CompanyCategories.company_id == company_id))
    result = await db.execute(stmt)
    services = result.all()

    # Map services to their categories
    for service, category in services:
        staff_members = await get_service_staff(db, service.id)
        service_response = CategoryServiceResponse(
            id=service.id,
            name=service.name,
            name_en=service.name_en,
            name_ee=service.name_ee,
            name_ru=service.name_ru,
            duration=service.duration,
            discount_price=service.discount_price,
            price=service.price,
            additional_info=service.additional_info,
            additional_info_en=service.additional_info_en,
            additional_info_ee=service.additional_info_ee,
            additional_info_ru=service.additional_info_ru,
            status=service.status,
            buffer_before=service.buffer_before,
            buffer_after=service.buffer_after,
            service_staff=staff_members,
            image_url=service.image_url
        )
        category_dict[str(category.id)]['services'].append(service_response)

    # Build hierarchical structure
    def build_category_hierarchy(cat_data) -> CompanyCategoryWithServicesResponse:
        cat = cat_data['category']
        subcats = []

        # Find subcategories by looking for categories that have this category as parent
        for other_cat_id, other_cat_data in category_dict.items():
            other_cat = other_cat_data['category']
            if other_cat.parent_category_id and str(other_cat.parent_category_id) == str(cat.id):
                subcats.append(build_category_hierarchy(other_cat_data))

        return CompanyCategoryWithServicesResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            parent_category_id=cat.parent_category_id,
            services=cat_data['services'],
            subcategories=subcats
        )

    # Get root categories (no parent) and build hierarchy
    result_list = []
    for cat_id, cat_data in category_dict.items():
        if cat_data['category'].parent_category_id is None:
            result_list.append(build_category_hierarchy(cat_data))

    return result_list


async def get_category(db: AsyncSession, category_id: str) -> Optional[CompanyCategories]:
    """
    Get a specific category by ID
    """
    stmt = select(CompanyCategories).filter(CompanyCategories.id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_category(db: AsyncSession, obj_in: CompanyCategoryCreate) -> CompanyCategories:
    """
    Create a new company category
    """
    db_obj = CompanyCategories(
        name=obj_in.name,
        name_en=obj_in.name_en,
        name_ru=obj_in.name_ru,
        name_ee=obj_in.name_ee,
        description_en=obj_in.description_en,
        description_ee=obj_in.description_ee,
        description_ru=obj_in.description_ru,
        company_id=obj_in.company_id,
        parent_category_id=obj_in.parent_category_id
    )

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update_category(db: AsyncSession, db_obj: CompanyCategories, obj_in: CompanyCategoryUpdate) -> CompanyCategories:
    """
    Update an existing company category
    """
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete_category(db: AsyncSession, category_id: str, company_id: str) -> bool:
    """
    Delete a company category
    """
    stmt = select(CompanyCategories).filter(
        CompanyCategories.id == category_id,
        CompanyCategories.company_id == company_id
    )
    result = await db.execute(stmt)
    db_obj = result.scalar_one_or_none()

    if not db_obj:
        return False

    await db.delete(db_obj)
    await db.commit()
    return True


async def get_company_categories(db: AsyncSession, company_id: str) -> List[CompanyCategories]:
    """
    Get all categories for a specific company with services count
    """
    stmt = (select(CompanyCategories)
            .options(selectinload(CompanyCategories.category_service))
            .filter(CompanyCategories.company_id == company_id))
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_company_categories_hierarchical(db: AsyncSession, company_id: str):
    """
    Get all categories for a company in hierarchical structure (parent categories with their subcategories)
    Returns only root categories (those without parent_category_id) with nested subcategories
    """
    from app.schemas.schemas import CompanyCategoryHierarchical

    # Get all categories for the company
    stmt = select(CompanyCategories).filter(CompanyCategories.company_id == company_id)
    result = await db.execute(stmt)
    all_categories = result.scalars().all()

    # Build a dictionary for quick lookup
    category_dict = {str(cat.id): cat for cat in all_categories}

    # Build hierarchical structure
    def build_hierarchy(category: CompanyCategories) -> CompanyCategoryHierarchical:
        subcats = [build_hierarchy(category_dict[str(sub.id)])
                   for sub in category.subcategories if str(sub.id) in category_dict]

        return CompanyCategoryHierarchical(
            id=category.id,
            company_id=category.company_id,
            parent_category_id=category.parent_category_id,
            name=category.name,
            name_en=category.name_en,
            name_ee=category.name_ee,
            name_ru=category.name_ru,
            description=category.description,
            description_en=category.description_en,
            description_ee=category.description_ee,
            description_ru=category.description_ru,
            created_at=category.created_at,
            updated_at=category.updated_at,
            services_count=category.services_count,
            has_subcategories=category.has_subcategories,
            subcategories=subcats
        )

    # Get root categories (no parent)
    root_categories = [cat for cat in all_categories if cat.parent_category_id is None]

    # Build hierarchy for each root
    return [build_hierarchy(cat) for cat in root_categories]


async def category_has_subcategories(db: AsyncSession, category_id: str) -> bool:
    """
    Check if a category has any subcategories
    """
    stmt = select(func.count()).select_from(CompanyCategories).filter(
        CompanyCategories.parent_category_id == category_id
    )
    result = await db.execute(stmt)
    count = result.scalar()
    return count > 0


async def validate_service_category(db: AsyncSession, category_id: str) -> tuple[bool, str]:
    """
    Validate if services can be added to this category.
    Returns (is_valid, error_message)

    Rules:
    - Services can only be added to categories that don't have subcategories
    """
    category = await get_category(db, category_id)
    if not category:
        return False, "Category not found"

    if await category_has_subcategories(db, category_id):
        return False, "Cannot add services to a category that has subcategories. Please add services to the subcategories instead."

    return True, ""


async def create_service(db: AsyncSession, obj_in: CategoryServiceCreate) -> CategoryServices:
    """
    Create a new service within a category
    Validates that the category doesn't have subcategories
    """
    # Validate category before creating service
    is_valid, error_msg = await validate_service_category(db, str(obj_in.category_id))
    if not is_valid:
        raise ValueError(error_msg)

    db_obj = CategoryServices(
        category_id=obj_in.category_id,
        name=obj_in.name,
        name_en=obj_in.name_en,
        name_ee=obj_in.name_ee,
        name_ru=obj_in.name_ru,
        duration=obj_in.duration,
        price=int(obj_in.price),  # Store price in cents
        discount_price=int((obj_in.discount_price or 0)),
        additional_info_ee=obj_in.additional_info_ee,
        additional_info_en=obj_in.additional_info_en,
        additional_info_ru=obj_in.additional_info_ru,
        status=obj_in.status,
        buffer_before=obj_in.buffer_before,
        buffer_after=obj_in.buffer_after,
        image_url=obj_in.image_url
    )

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)

    # Assign staff members to the service
    if obj_in.staff_ids:
        await assign_staff_to_service(db, db_obj.id, obj_in.staff_ids)

    await db.refresh(db_obj)
    return db_obj


async def update_service(db: AsyncSession, db_obj: CategoryServices, obj_in: CategoryServiceUpdate) -> CategoryServices:
    """
    Update an existing service
    Validates category if being changed
    """
    # Validate new category if provided
    if obj_in.category_id and str(obj_in.category_id) != str(db_obj.category_id):
        is_valid, error_msg = await validate_service_category(db, str(obj_in.category_id))
        if not is_valid:
            raise ValueError(error_msg)

    # Handle price conversion
    if obj_in.price is not None:
        obj_in.price = int(obj_in.price * 100)
    if obj_in.discount_price is not None:
        obj_in.discount_price = int(obj_in.discount_price * 100)

    update_data = obj_in.model_dump(exclude_unset=True)

    # Handle staff_ids and remove_image separately
    staff_ids = update_data.pop('staff_ids', None)
    remove_image = update_data.pop('remove_image', False)

    # Handle image removal
    if remove_image:
        update_data['image_url'] = None

    # Update service fields
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)

    # Update staff assignments if provided
    if staff_ids is not None:
        # Remove existing assignments
        stmt = delete(ServiceStaff).filter(ServiceStaff.service_id == db_obj.id)
        await db.execute(stmt)
        await db.commit()

        # Add new assignments
        if staff_ids:
            await assign_staff_to_service(db, db_obj.id, staff_ids)

    return db_obj


async def assign_staff_to_service(db: AsyncSession, service_id: UUID4, staff_ids: List[UUID4]) -> None:
    """
    Assign multiple staff members to a service
    """
    for staff_id in staff_ids:
        # Check if assignment already exists
        stmt = (select(ServiceStaff)
            .options(selectinload(ServiceStaff.user))
            .filter(
                ServiceStaff.service_id == service_id,
                ServiceStaff.user_id == staff_id
            ))
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            staff_assignment = ServiceStaff(
                service_id=service_id,
                user_id=staff_id
            )
            db.add(staff_assignment)

    await db.commit()


async def get_service_staff(db: AsyncSession, service_id: UUID4) -> List[ServiceStaff]:
    """
    Get all staff members assigned to a service
    """
    stmt = (select(ServiceStaff)
            .options(selectinload(ServiceStaff.user))
            .options(selectinload(ServiceStaff.service))
            .filter(ServiceStaff.service_id == service_id))
    result = await db.execute(stmt)
    staff = result.scalars().all()
    return staff


async def remove_staff_from_service(db: AsyncSession, service_id: UUID4, staff_id: UUID4) -> bool:
    """
    Remove a staff member from a service
    """
    stmt = select(ServiceStaff).filter(
        ServiceStaff.service_id == service_id,
        ServiceStaff.user_id == staff_id
    )
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()

    if assignment:
        await db.delete(assignment)
        await db.commit()
        return True
    return False


async def copy_service(db: AsyncSession, service_id: str, company_id: str) -> Optional[CategoryServices]:
    """
    Create a copy of an existing service with all its properties and staff assignments.
    The copied service will have " (Copy)" appended to its name.
    """
    # Get the original service
    original_service = await get_service(db=db, service_id=service_id, company_id=company_id)
    if not original_service:
        return None

    # Get staff assignments for the original service
    staff_assignments = await get_service_staff(db=db, service_id=original_service.id)
    staff_ids = [assignment.user_id for assignment in staff_assignments]

    # Create a new service with copied data
    new_service = CategoryServices(
        category_id=original_service.category_id,
        name=f"{original_service.name} (Copy)" if original_service.name else None,
        name_en=f"{original_service.name_en} (Copy)" if original_service.name_en else None,
        name_ee=f"{original_service.name_ee} (Copy)" if original_service.name_ee else None,
        name_ru=f"{original_service.name_ru} (Copy)" if original_service.name_ru else None,
        duration=original_service.duration,
        price=original_service.price,
        discount_price=original_service.discount_price,
        additional_info_ee=original_service.additional_info_ee,
        additional_info_en=original_service.additional_info_en,
        additional_info_ru=original_service.additional_info_ru,
        status=original_service.status,
        buffer_before=original_service.buffer_before,
        buffer_after=original_service.buffer_after,
        image_url=original_service.image_url  # Copy the same image URL
    )

    db.add(new_service)
    await db.commit()
    await db.refresh(new_service)

    # Copy staff assignments
    if staff_ids:
        await assign_staff_to_service(db, new_service.id, staff_ids)

    return new_service


async def delete_service(db: AsyncSession, service_id: UUID4, company_id: Optional[UUID4] = None) -> bool:
    """
    Delete a service and any staff assignments tied to it.

    If company_id is provided, ensure the service belongs to a category for that company
    before deleting (extra safety).

    Returns True when deletion happened, False when the service was not found or the
    company check failed.
    """
    # If company_id is provided, ensure the service belongs to that company
    if company_id:
        stmt = (select(CategoryServices)
                .join(CompanyCategories, CategoryServices.category_id == CompanyCategories.id)
                .filter(CategoryServices.id == service_id, CompanyCategories.company_id == company_id))
        result = await db.execute(stmt)
        service = result.scalar_one_or_none()
    else:
        stmt = select(CategoryServices).filter(CategoryServices.id == service_id)
        result = await db.execute(stmt)
        service = result.scalar_one_or_none()

    if not service:
        return False

    # Remove any ServiceStaff assignments for this service
    stmt = delete(ServiceStaff).filter(ServiceStaff.service_id == service_id)
    await db.execute(stmt)

    # Delete the service itself
    await db.delete(service)
    await db.commit()
    return True
