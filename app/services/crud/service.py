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
    Get all services for a company grouped by category with assigned staff
    Returns a dictionary where keys are categories and values are lists of services
    """
    # Get all services for the company
    services = (db.query(CompanyCategories.name, CompanyCategories.id, CategoryServices, CompanyCategories.description)
                .join(CompanyCategories, CategoryServices.category_id==CompanyCategories.id).filter(
                CompanyCategories.company_id == company_id
    ).all())
    comp_categories = defaultdict(list)
    for service in services:
        staff_members = get_service_staff(db, service[2].id)
        comp_categories[(service[0], service[1], service[3])].append(CategoryServiceResponse(
            id=service[2].id,
            name=service[2].name,
            name_en=service[2].name_en,
            name_ee=service[2].name_ee,
            name_ru=service[2].name_ru,
            duration=service[2].duration,
            discount_price=service[2].discount_price,
            price=service[2].price,
            additional_info=service[2].additional_info,
            additional_info_en=service[2].additional_info_en,
            additional_info_ee=service[2].additional_info_ee,
            additional_info_ru=service[2].additional_info_ru,
            status=service[2].status,
            buffer_before=service[2].buffer_before,
            buffer_after=service[2].buffer_after,
            service_staff=staff_members,
            image_url=service[2].image_url
        ))

    result = []
    for category, services in comp_categories.items():
        result.append(CompanyCategoryWithServicesResponse(
            name=category[0],
            id = category[1],
            description=category[2],
            services=services
        ))

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
        company_id=obj_in.company_id
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


def create_service(db: Session, obj_in: CategoryServiceCreate) -> CategoryServices:
    """
    Create a new service within a category
    """
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
