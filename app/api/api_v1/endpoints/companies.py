from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.models import Users
from app.schemas import CompanyCreate, User, Company
from app.services.crud import company as crud_company

router = APIRouter()


@router.post("", response_model=Company, status_code=status.HTTP_201_CREATED)
async def create_company(
    *,
    db: Session = Depends(get_db),
    company_in: CompanyCreate,
    current_user: User = Depends(get_current_active_user)
) -> Company:
    """
    Create a new company.
    """
    company = crud_company.create(db=db, obj_in=company_in, current_user=current_user)
    return company

#
# @router.post("/add-member", response_model=BusinessStaff, status_code=status.HTTP_201_CREATED)
# async def add_business_member(
#     *,
#     db: Session = Depends(get_db),
#     business_staff_in: BusinessStaffCreate,
#     current_professional: Professional = Depends(get_current_active_professional)
# ) -> BusinessStaff:
#     """
#     Add a new member to the business.
#     """
#     business = crud_business.business.get(db=db, id=business_staff_in.business_id)
#     if not business:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Business not found"
#         )
#     if business.owner_id != current_professional.id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not enough permissions to add members to this business"
#         )
#     business_staff_in.professional_id = current_professional.id
#     business_staff = crud_business.business_staff.create(db=db, obj_in=business_staff_in)
#     return business_staff
#
#
# @router.get("/my-businesses", response_model=List[BusinessWithDetails])
# async def get_my_businesses(
#     db: Session = Depends(get_db),
#     current_professional: Professional = Depends(get_current_active_professional),
#     skip: int = 0,
#     limit: int = 10,
# ) -> List[Business]:
#     """
#     Get all businesses owned by the authenticated professional.
#     """
#     businesses = crud_business.business.get_multi_by_owner(
#         db=db,
#         owner_id=current_professional.id,
#         skip=skip,
#         limit=limit
#     )
#     return businesses
#
#
# @router.get("/{business_id}", response_model=BusinessWithDetails)
# async def get_business(
#     *,
#     db: Session = Depends(get_db),
#     business_id: int,
#     current_professional: Professional = Depends(get_current_active_professional)
# ) -> Business:
#     """
#     Get a specific business by ID.
#     Only the owner can access their business details.
#     """
#     business = crud_business.business.get(db=db, id=business_id)
#     if not business:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Business not found"
#         )
#     if business.owner_id != current_professional.id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not enough permissions to access this business"
#         )
#     return business
