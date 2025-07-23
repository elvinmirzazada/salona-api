from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import Client, ClientCreate, ClientUpdate
from app.services.crud import client as crud_client, business as crud_business

router = APIRouter()


@router.post("/", response_model=Client, status_code=status.HTTP_201_CREATED)
def create_client(
    *,
    db: Session = Depends(get_db),
    client_in: ClientCreate
) -> Client:
    """
    Create a new client.
    """
    # Verify that the business exists
    business = crud_business.get(db=db, id=client_in.business_id)
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    # Check if client with this phone number already exists for this business
    existing_client = crud_client.get_by_phone_and_business(
        db=db, 
        phone_number=client_in.phone_number, 
        business_id=client_in.business_id
    )
    if existing_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client with this phone number already exists for this business"
        )
    
    client = crud_client.create(db=db, obj_in=client_in)
    return client


@router.get("/{client_id}", response_model=Client)
def get_client(
    client_id: int,
    db: Session = Depends(get_db)
) -> Client:
    """
    Get client by ID.
    """
    client = crud_client.get(db=db, id=client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    return client


@router.get("/business/{business_id}", response_model=List[Client])
def get_clients_by_business(
    business_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> List[Client]:
    """
    Get all clients for a business.
    """
    clients = crud_client.get_multi_by_business(db=db, business_id=business_id, skip=skip, limit=limit)
    return clients


@router.put("/{client_id}", response_model=Client)
def update_client(
    *,
    db: Session = Depends(get_db),
    client_id: int,
    client_in: ClientUpdate
) -> Client:
    """
    Update client.
    """
    client = crud_client.get(db=db, id=client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    client = crud_client.update(db=db, db_obj=client, obj_in=client_in)
    return client
