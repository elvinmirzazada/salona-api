from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_professional
from app.db.session import get_db
from app.models.models import Professional, Business
from app.schemas import BusinessCreate, Business as BusinessSchema, BusinessWithDetails, BusinessStaff, BusinessStaffCreate
from app.services import crud as crud_business

router = APIRouter()


@router.post("/", response_model=BusinessSchema, status_code=status.HTTP_201_CREATED)
async def create_business(
    *,
    db: Session = Depends(get_db),
    business_in: BusinessCreate,
    current_professional: Professional = Depends(get_current_active_professional)
) -> Business:
    """
    Create a new business.
    """
    # Set the owner_id from the authenticated professional
    business_in.owner_id = current_professional.id
    business = crud_business.business.create(db=db, obj_in=business_in)
    crud_business.business_staff.create(
        db=db,
        obj_in=BusinessStaffCreate(
            business_id=business.id,
            professional_id=current_professional.id
        )
    )
    return business


@router.post("/add-member", response_model=BusinessStaff, status_code=status.HTTP_201_CREATED)
async def add_business_member(
    *,
    db: Session = Depends(get_db),
    business_staff_in: BusinessStaffCreate,
    current_professional: Professional = Depends(get_current_active_professional)
) -> BusinessStaff:
    """
    Add a new member to the business.
    """
    business = crud_business.business.get(db=db, id=business_staff_in.business_id)
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    if business.owner_id != current_professional.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to add members to this business"
        )
    business_staff_in.professional_id = current_professional.id
    business_staff = crud_business.business_staff.create(db=db, obj_in=business_staff_in)
    return business_staff


@router.get("/my-businesses", response_model=List[BusinessWithDetails])
async def get_my_businesses(
    db: Session = Depends(get_db),
    current_professional: Professional = Depends(get_current_active_professional),
    skip: int = 0,
    limit: int = 10,
) -> List[Business]:
    """
    Get all businesses owned by the authenticated professional.
    """
    businesses = crud_business.business.get_multi_by_owner(
        db=db,
        owner_id=current_professional.id,
        skip=skip,
        limit=limit
    )
    return businesses


@router.get("/{business_id}", response_model=BusinessWithDetails)
async def get_business(
    *,
    db: Session = Depends(get_db),
    business_id: int,
    current_professional: Professional = Depends(get_current_active_professional)
) -> Business:
    """
    Get a specific business by ID.
    Only the owner can access their business details.
    """
    business = crud_business.business.get(db=db, id=business_id)
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    if business.owner_id != current_professional.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this business"
        )
    return business
