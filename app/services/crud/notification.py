from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from pydantic import UUID4

from app.models.models import CompanyNotifications
from app.schemas import NotificationCreate, NotificationUpdate, Notification
from app.schemas.responses import PaginationInfo


def create_company_notification(db: Session, notification: NotificationCreate) -> Notification:
    """Create a new notification"""
    db_notification = CompanyNotifications(**notification.model_dump())
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def get_notification(db: Session, notification_id: UUID4) -> Optional[CompanyNotifications]:
    """Get a notification by ID"""
    return db.query(CompanyNotifications).filter(CompanyNotifications.id == notification_id).first()


def get_user_notifications(
    db: Session, 
    company_id: UUID4,
    page: int = 1, 
    per_page: int = 20,
    status_filter: Optional[str] = None
) -> tuple[List[Notification], PaginationInfo]:
    """Get paginated notifications for a user"""
    query = db.query(CompanyNotifications).filter(CompanyNotifications.company_id == company_id)
    
    # Apply status filter if provided
    if status_filter:
        query = query.filter(CompanyNotifications.status == status_filter)
    
    # Order by created_at descending (newest first)
    query = query.order_by(CompanyNotifications.created_at.desc())
    
    # Calculate total count
    total = query.count()
    
    # Calculate pagination
    offset = (page - 1) * per_page
    notifications = query.offset(offset).limit(per_page).all()
    
    total_pages = (total + per_page - 1) // per_page
    
    pagination_info = PaginationInfo(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )
    
    return notifications, pagination_info


def update_notification(
    db: Session, 
    notification_id: UUID4, 
    notification_update: NotificationUpdate
) -> Optional[CompanyNotifications]:
    """Update a notification"""
    db_notification = db.query(CompanyNotifications).filter(CompanyNotifications.id == notification_id).first()
    if db_notification:
        update_data = notification_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_notification, key, value)
        db.commit()
        db.refresh(db_notification)
    return db_notification


def delete_notification(db: Session, notification_id: UUID4) -> bool:
    """Delete a notification"""
    db_notification = db.query(CompanyNotifications).filter(CompanyNotifications.id == notification_id).first()
    if db_notification:
        db.delete(db_notification)
        db.commit()
        return True
    return False


def mark_notifications_as_read(db: Session, company_id: UUID4, notification_ids: List[UUID4]) -> int:
    """Mark multiple notifications as read"""
    from app.models.enums import NotificationStatus
    
    count = db.query(CompanyNotifications).filter(
        and_(
            CompanyNotifications.company_id == company_id,
            CompanyNotifications.id.in_(notification_ids)
        )
    ).update({"status": NotificationStatus.READ}, synchronize_session=False)
    
    db.commit()
    return count


def mark_all_notifications_as_read(db: Session, user_id: UUID4) -> int:
    """Mark all notifications as read for a user"""
    from app.models.enums import NotificationStatus
    
    count = db.query(CompanyNotifications).filter(
        and_(
            CompanyNotifications.user_id == user_id,
            CompanyNotifications.status == NotificationStatus.UNREAD
        )
    ).update({"status": NotificationStatus.READ}, synchronize_session=False)
    
    db.commit()
    return count


def get_unread_count(db: Session, company_id: UUID4) -> int:
    """Get count of unread notifications for a user"""
    from app.models.enums import NotificationStatus
    
    return db.query(func.count(CompanyNotifications.id)).filter(
        and_(
            CompanyNotifications.company_id == company_id,
            CompanyNotifications.status == NotificationStatus.UNREAD
        )
    ).scalar()
