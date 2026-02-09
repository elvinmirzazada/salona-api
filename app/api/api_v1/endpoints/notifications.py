from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import UUID4

from app.db.session import get_db
from app.schemas.schemas import Notification, CompanyNotificationCreate, NotificationUpdate
from app.schemas.responses import DataResponse, PaginatedResponse
from app.services.crud import notification as crud_notification
from app.api.dependencies import get_current_user, get_current_company_id
from app.models.enums import NotificationStatus


router = APIRouter()


@router.get("", response_model=PaginatedResponse[List[Notification]])
async def get_company_notifications(
    *,
    db: Session = Depends(get_db),
    company_id = Depends(get_current_company_id),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[NotificationStatus] = Query(None, description="Filter by notification status")
) -> PaginatedResponse[List[Notification]]:
    """
    Get paginated notifications for the current user
    """
    notifications, pagination_info = crud_notification.get_user_notifications(
        db=db,
        company_id=company_id,
        page=page,
        per_page=per_page,
        status_filter=status_filter.value if status_filter else None
    )
    return PaginatedResponse.success_response(
        data=notifications,
        pagination=pagination_info,
        message="Notifications retrieved successfully"
    )


@router.get("/unread-count", response_model=DataResponse[dict])
async def get_unread_count(
    *,
    db: Session = Depends(get_db),
    company_id = Depends(get_current_company_id)
) -> DataResponse[dict]:
    """
    Get count of unread notifications for the current user
    """
    count = crud_notification.get_unread_count(db=db, company_id=company_id)
    
    return DataResponse.success_response(
        data={'unread_count': count},
        message="Unread count retrieved successfully"
    )


@router.get("/all-count", response_model=DataResponse[dict])
async def get_all_count(
    *,
    db: Session = Depends(get_db),
    company_id = Depends(get_current_company_id)
) -> DataResponse[dict]:
    """
    Get count of all notifications for the current company
    """
    count = crud_notification.get_all_count(db=db, company_id=company_id)

    return DataResponse.success_response(
        data={'all_count': count},
        message="All notifications count retrieved successfully"
    )


@router.get("/{notification_id}", response_model=DataResponse[Notification])
async def get_notification(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    notification_id: UUID4
) -> DataResponse[Notification]:
    """
    Get a specific notification by ID
    """
    notification = crud_notification.get_notification(db=db, notification_id=notification_id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Check if notification belongs to current user
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return DataResponse.success_response(
        data=notification,
        message="Notification retrieved successfully"
    )


@router.patch("/{notification_id}", response_model=DataResponse[Notification])
async def update_notification(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    notification_id: UUID4,
    notification_update: NotificationUpdate
) -> DataResponse[Notification]:
    """
    Update a notification (typically to mark as read/archived)
    """
    # Check if notification exists and belongs to user
    existing_notification = crud_notification.get_notification(db=db, notification_id=notification_id)
    
    if not existing_notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    if existing_notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    updated_notification = crud_notification.update_notification(
        db=db,
        notification_id=notification_id,
        notification_update=notification_update
    )
    
    return DataResponse.success_response(
        data=updated_notification,
        message="Notification updated successfully"
    )


@router.delete("/{notification_id}", response_model=DataResponse[dict])
async def delete_notification(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    company_id = Depends(get_current_company_id),
    notification_id: UUID4
) -> DataResponse[dict]:
    """
    Delete a notification
    """
    # Check if notification exists and belongs to user
    existing_notification = crud_notification.get_notification(db=db, notification_id=notification_id)
    
    if not existing_notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    if str(existing_notification.company_id) != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    success = crud_notification.delete_notification(db=db, notification_id=notification_id)
    
    if success:
        return DataResponse.success_response(
            data={"deleted": True},
            message="Notification deleted successfully"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete notification"
        )


@router.post("/mark-as-read/{notification_id}", response_model=DataResponse[dict])
async def mark_notifications_as_read(
    *,
    db: Session = Depends(get_db),
    company_id = Depends(get_current_company_id),
    notification_id: str
) -> DataResponse[dict]:
    """
    Mark multiple notifications as read
    """
    count = crud_notification.mark_notifications_as_read(
        db=db,
        company_id=company_id,
        notification_ids=[notification_id]
    )
    
    return DataResponse.success_response(
        data={"marked_as_read": count},
        message=f"Marked {count} notifications as read"
    )


@router.patch("/mark-all/as-read", response_model=DataResponse[dict])
async def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    company_id = Depends(get_current_company_id)
) -> DataResponse[dict]:
    """
    Mark all notifications as read for the current user
    """
    count = crud_notification.mark_all_notifications_as_read(
        db=db,
        company_id=company_id
    )
    
    return DataResponse.success_response(
        data={"marked_as_read": count},
        message=f"Marked {count} notifications as read"
    )


@router.post("", response_model=DataResponse[Notification], status_code=status.HTTP_201_CREATED)
async def create_notification(
    *,
    db: Session = Depends(get_db),
    company_id = Depends(get_current_company_id),
    notification_in: CompanyNotificationCreate
) -> DataResponse[Notification]:
    """
    Create a new notification (for admin/system use)
    """
    notification_in.company_id = company_id
    notification = crud_notification.create_company_notification(db=db, notification=notification_in)
    
    return DataResponse.success_response(
        data=notification,
        message="Notification created successfully",
        status_code=status.HTTP_201_CREATED
    )
