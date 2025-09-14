# from typing import List
# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from app.db.session import get_db
# from app.schemas.schemas import Service, ServiceCreate, ServiceUpdate, ServiceWithDetails
# from app.services.crud import service as crud_service, business as crud_business
#
# router = APIRouter()
#
#
# @router.post("/", response_model=Service, status_code=status.HTTP_201_CREATED)
# def create_service(
#     *,
#     db: Session = Depends(get_db),
#     service_in: ServiceCreate
# ) -> Service:
#     """
#     Create a new service.
#     """
#     # Verify that the business exists
#     business = crud_business.get(db=db, id=service_in.business_id)
#     if not business:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Business not found"
#         )
#
#     service = crud_service.create(db=db, obj_in=service_in)
#     return service
#
#
# @router.get("/{service_id}", response_model=ServiceWithDetails)
# def get_service(
#     service_id: int,
#     db: Session = Depends(get_db)
# ) -> Service:
#     """
#     Get service by ID with details.
#     """
#     service = crud_service.get(db=db, id=service_id)
#     if not service:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Service not found"
#         )
#     return service
#
#
# @router.get("/business/{business_id}", response_model=List[Service])
# def get_services_by_business(
#     business_id: int,
#     skip: int = 0,
#     limit: int = 100,
#     db: Session = Depends(get_db)
# ) -> List[Service]:
#     """
#     Get all services for a business.
#     """
#     services = crud_service.get_multi_by_business(db=db, business_id=business_id, skip=skip, limit=limit)
#     return services
#
#
# @router.put("/{service_id}", response_model=Service)
# def update_service(
#     *,
#     db: Session = Depends(get_db),
#     service_id: int,
#     service_in: ServiceUpdate
# ) -> Service:
#     """
#     Update service.
#     """
#     service = crud_service.get(db=db, id=service_id)
#     if not service:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Service not found"
#         )
#
#     service = crud_service.update(db=db, db_obj=service, obj_in=service_in)
#     return service
