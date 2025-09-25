from typing import Optional, Dict, List
from collections import defaultdict
from pydantic.v1 import UUID4
from sqlalchemy.orm import Session

from app.models.models import CategoryServices, CompanyCategories
from app.schemas import CategoryServiceResponse
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
    Get all services for a company grouped by category
    Returns a dictionary where keys are categories and values are lists of services
    """
    # Get all services for the company
    services = (db.query(CompanyCategories.name, CategoryServices)
                .join(CompanyCategories, CategoryServices.category_id==CompanyCategories.id).filter(
                CompanyCategories.company_id == company_id
    ).all())
    comp_categories = defaultdict(list)
    for service in services:
        comp_categories[service[0]].append(CategoryServiceResponse(
            id=service[1].id,
            name=service[1].name,
            duration=service[1].duration,
            discount_price=service[1].discount_price,
            price=service[1].price,
            additional_info=service[1].additional_info,
            status=service[1].status
        ))

    result = []
    for category, services in comp_categories.items():
        result.append(CompanyCategoryWithServicesResponse(
            name=category,
            services=services
        ))

    return result
