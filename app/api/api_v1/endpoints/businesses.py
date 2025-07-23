from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import Business, BusinessCreate, BusinessUpdate, BusinessWithDetails
from app.services.crud import business as crud_business, professional as crud_professional

router = APIRouter()


@router.post("/", response_model=Business, status_code=status.HTTP_201_CREATED)
def create_business(
    *,
    db: Session = Depends(get_db),
    business_in: BusinessCreate
) -> Business:
    """
    Create a new business.
    """
    # Verify that the owner (professional) exists
    professional = crud_professional.get(db=db, id=business_in.owner_id)
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional not found"
        )
    
    business = crud_business.create(db=db, obj_in=business_in)
    return business


@router.get("/{business_id}", response_model=BusinessWithDetails)
def get_business(
    business_id: int,
    db: Session = Depends(get_db)
) -> Business:
    """
    Get business by ID with details.
    """
    business = crud_business.get(db=db, id=business_id)
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    return business


@router.get("/owner/{owner_id}", response_model=List[Business])
def get_businesses_by_owner(
    owner_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> List[Business]:
    """
    Get all businesses owned by a professional.
    """
    businesses = crud_business.get_multi_by_owner(db=db, owner_id=owner_id, skip=skip, limit=limit)
    return businesses


@router.put("/{business_id}", response_model=Business)
def update_business(
    *,
    db: Session = Depends(get_db),
    business_id: int,
    business_in: BusinessUpdate
) -> Business:
    """
    Update business.
    """
    business = crud_business.get(db=db, id=business_id)
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    business = crud_business.update(db=db, db_obj=business, obj_in=business_in)
    return business
