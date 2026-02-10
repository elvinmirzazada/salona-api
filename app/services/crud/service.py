from typing import Optional, Dict, List
from collections import defaultdict
from pydantic.v1 import UUID4
from sqlalchemy.orm import Session
from sqlalchemy import func

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


def get_service(db: Session, service_id: str, company_id: str) -> Optional[CategoryServices]:
    """
    Get all services for a company grouped by category
    Returns a dictionary where keys are categories and values are lists of services
    """
    service = (db.query(CategoryServices)
                .join(CompanyCategories, CategoryServices.category_id==CompanyCategories.id).filter(
                CompanyCategories.company_id == company_id, CategoryServices.id == service_id
    ).one_or_none())

    return service


def get_company_services(db: Session, company_id: str) -> List[CompanyCategoryWithServicesResponse]:
    """
    Get all services for a company grouped by category with assigned staff in hierarchical structure
    Returns categories with their services and subcategories
    """
    # Get all categories and services for the company
    all_categories = db.query(CompanyCategories).filter(
        CompanyCategories.company_id == company_id
    ).all()

    # Build a dictionary for quick lookup
    category_dict = {}
    for cat in all_categories:
        category_dict[str(cat.id)] = {
            'category': cat,
            'services': [],
            'subcategories': []
        }

    # Get all services for the company
    services = (db.query(CategoryServices, CompanyCategories)
                .join(CompanyCategories, CategoryServices.category_id == CompanyCategories.id)
                .filter(CompanyCategories.company_id == company_id)
                .all())

    # Map services to their categories
    for service, category in services:
        staff_members = get_service_staff(db, service.id)
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

        # Find and build subcategories
        if cat and cat.subcategories:
            for sub_cat in cat.subcategories:
                if str(sub_cat.id) in category_dict:
                    subcats.append(build_category_hierarchy(category_dict[str(sub_cat.id)]))

        return CompanyCategoryWithServicesResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            parent_category_id=cat.parent_category_id,
            services=cat_data['services'],
            subcategories=subcats
        )

    # Get root categories (no parent) and build hierarchy
    result = []
    for cat_id, cat_data in category_dict.items():
        if cat_data['category'].parent_category_id is None:
            result.append(build_category_hierarchy(cat_data))

    return result


def get_category(db: Session, category_id: str) -> Optional[CompanyCategories]:
    """
    Get a specific category by ID
    """
    return db.query(CompanyCategories).filter(CompanyCategories.id == category_id).first()


def create_category(db: Session, obj_in: CompanyCategoryCreate) -> CompanyCategories:
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
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_category(db: Session, db_obj: CompanyCategories, obj_in: CompanyCategoryUpdate) -> CompanyCategories:
    """
    Update an existing company category
    """
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_category(db: Session, category_id: str, company_id: str) -> bool:
    """
    Delete a company category
    """
    db_obj = db.query(CompanyCategories).filter(CompanyCategories.id == category_id, CompanyCategories.company_id==company_id).first()
    if not db_obj:
        return False

    db.delete(db_obj)
    db.commit()
    return True


def get_company_categories(db: Session, company_id: str) -> List[CompanyCategories]:
    """
    Get all categories for a specific company with services count
    """
    return db.query(CompanyCategories).filter(CompanyCategories.company_id == company_id).all()


def get_company_categories_hierarchical(db: Session, company_id: str):
    """
    Get all categories for a company in hierarchical structure (parent categories with their subcategories)
    Returns only root categories (those without parent_category_id) with nested subcategories
    """
    from app.schemas.schemas import CompanyCategoryHierarchical

    # Get all categories for the company
    all_categories = db.query(CompanyCategories).filter(
        CompanyCategories.company_id == company_id
    ).all()

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


def category_has_subcategories(db: Session, category_id: str) -> bool:
    """
    Check if a category has any subcategories
    """
    count = db.query(CompanyCategories).filter(
        CompanyCategories.parent_category_id == category_id
    ).count()
    return count > 0


def validate_service_category(db: Session, category_id: str) -> tuple[bool, str]:
    """
    Validate if services can be added to this category.
    Returns (is_valid, error_message)

    Rules:
    - Services can only be added to categories that don't have subcategories
    """
    category = get_category(db, category_id)
    if not category:
        return False, "Category not found"

    if category_has_subcategories(db, category_id):
        return False, "Cannot add services to a category that has subcategories. Please add services to the subcategories instead."

    return True, ""


def create_service(db: Session, obj_in: CategoryServiceCreate) -> CategoryServices:
    """
    Create a new service within a category
    Validates that the category doesn't have subcategories
    """
    # Validate category before creating service
    is_valid, error_msg = validate_service_category(db, str(obj_in.category_id))
    if not is_valid:
        raise ValueError(error_msg)

    db_obj = CategoryServices(
        category_id=obj_in.category_id,
        name=obj_in.name,
        name_en=obj_in.name_en,
        name_ee=obj_in.name_ee,
        name_ru=obj_in.name_ru,
        duration=obj_in.duration,
        price=int(obj_in.price * 100),  # Store price in cents
        discount_price=int(obj_in.discount_price * 100),
        additional_info_ee=obj_in.additional_info_ee,
        additional_info_en=obj_in.additional_info_en,
        additional_info_ru=obj_in.additional_info_ru,
        status=obj_in.status,
        buffer_before=obj_in.buffer_before,
        buffer_after=obj_in.buffer_after,
        image_url=obj_in.image_url
    )

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    # Assign staff members to the service
    if obj_in.staff_ids:
        assign_staff_to_service(db, db_obj.id, obj_in.staff_ids)

    return db_obj


def update_service(db: Session, db_obj: CategoryServices, obj_in: CategoryServiceUpdate) -> CategoryServices:
    """
    Update an existing service
    """
    obj_in.price = int(obj_in.price * 100) if obj_in.price is not None else 0
    obj_in.discount_price = int(obj_in.discount_price * 100) if obj_in.discount_price is not None else 0
    update_data = obj_in.model_dump(exclude_unset=True)

    # Handle staff_ids separately
    staff_ids = update_data.pop('staff_ids', None)

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    # Update staff assignments if provided
    if staff_ids is not None:
        # Remove existing assignments
        db.query(ServiceStaff).filter(ServiceStaff.service_id == db_obj.id).delete()
        db.commit()

        # Add new assignments
        if staff_ids:
            assign_staff_to_service(db, db_obj.id, staff_ids)

    return db_obj


def assign_staff_to_service(db: Session, service_id: UUID4, staff_ids: List[UUID4]) -> None:
    """
    Assign multiple staff members to a service
    """
    for staff_id in staff_ids:
        # Check if assignment already exists
        existing = db.query(ServiceStaff).filter(
            ServiceStaff.service_id == service_id,
            ServiceStaff.user_id == staff_id
        ).first()

        if not existing:
            staff_assignment = ServiceStaff(
                service_id=service_id,
                user_id=staff_id
            )
            db.add(staff_assignment)

    db.commit()


def get_service_staff(db: Session, service_id: UUID4) -> List[ServiceStaff]:
    """
    Get all staff members assigned to a service
    """
    staff = (db.query(ServiceStaff)
             .filter(ServiceStaff.service_id == service_id)
             .all())
    return staff


def remove_staff_from_service(db: Session, service_id: UUID4, staff_id: UUID4) -> bool:
    """
    Remove a staff member from a service
    """
    assignment = db.query(ServiceStaff).filter(
        ServiceStaff.service_id == service_id,
        ServiceStaff.user_id == staff_id
    ).first()

    if assignment:
        db.delete(assignment)
        db.commit()
        return True
    return False


def delete_service(db: Session, service_id: UUID4, company_id: Optional[UUID4] = None) -> bool:
    """
    Delete a service and any staff assignments tied to it.

    If company_id is provided, ensure the service belongs to a category for that company
    before deleting (extra safety).

    Returns True when deletion happened, False when the service was not found or the
    company check failed.
    """
    # If company_id is provided, ensure the service belongs to that company
    if company_id:
        service = (db.query(CategoryServices)
                   .join(CompanyCategories, CategoryServices.category_id == CompanyCategories.id)
                   .filter(CategoryServices.id == service_id, CompanyCategories.company_id == company_id)
                   .one_or_none())
    else:
        service = db.query(CategoryServices).filter(CategoryServices.id == service_id).one_or_none()

    if not service:
        return False

    # Remove any ServiceStaff assignments for this service
    db.query(ServiceStaff).filter(ServiceStaff.service_id == service_id).delete(synchronize_session=False)

    # Delete the service itself
    db.delete(service)
    db.commit()
    return True
