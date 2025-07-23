from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import Appointment, AppointmentCreate, AppointmentUpdate, AppointmentWithDetails
from app.services.crud import appointment as crud_appointment, service as crud_service, client as crud_client, business as crud_business

router = APIRouter()


@router.post("/", response_model=Appointment, status_code=status.HTTP_201_CREATED)
def create_appointment(
    *,
    db: Session = Depends(get_db),
    appointment_in: AppointmentCreate
) -> Appointment:
    """
    Create a new appointment.
    """
    # Verify that the business exists
    business = crud_business.get(db=db, id=appointment_in.business_id)
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    # Verify that the service exists and belongs to the business
    service = crud_service.get(db=db, id=appointment_in.service_id)
    if not service or service.business_id != appointment_in.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or doesn't belong to this business"
        )
    
    # Verify that the client exists and belongs to the business
    client = crud_client.get(db=db, id=appointment_in.client_id)
    if not client or client.business_id != appointment_in.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found or doesn't belong to this business"
        )
    
    # Validate appointment times
    if appointment_in.start_time >= appointment_in.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be before end time"
        )
    
    if appointment_in.start_time < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create appointment in the past"
        )
    
    appointment = crud_appointment.create(db=db, obj_in=appointment_in)
    return appointment


@router.get("/{appointment_id}", response_model=AppointmentWithDetails)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db)
) -> Appointment:
    """
    Get appointment by ID with details.
    """
    appointment = crud_appointment.get(db=db, id=appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


@router.get("/business/{business_id}", response_model=List[Appointment])
def get_appointments_by_business(
    business_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> List[Appointment]:
    """
    Get all appointments for a business.
    """
    appointments = crud_appointment.get_multi_by_business(db=db, business_id=business_id, skip=skip, limit=limit)
    return appointments


@router.get("/client/{client_id}", response_model=List[Appointment])
def get_appointments_by_client(
    client_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> List[Appointment]:
    """
    Get all appointments for a client.
    """
    appointments = crud_appointment.get_multi_by_client(db=db, client_id=client_id, skip=skip, limit=limit)
    return appointments


@router.put("/{appointment_id}", response_model=Appointment)
def update_appointment(
    *,
    db: Session = Depends(get_db),
    appointment_id: int,
    appointment_in: AppointmentUpdate
) -> Appointment:
    """
    Update appointment.
    """
    appointment = crud_appointment.get(db=db, id=appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # If updating times, validate them
    if appointment_in.start_time and appointment_in.end_time:
        if appointment_in.start_time >= appointment_in.end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be before end time"
            )
    
    appointment = crud_appointment.update(db=db, db_obj=appointment, obj_in=appointment_in)
    return appointment
