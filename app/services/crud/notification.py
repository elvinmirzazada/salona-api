from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, select, update
from pydantic import UUID4

from app.models import NotificationStatus
from app.models.models import CompanyNotifications
from app.schemas import NotificationCreate, NotificationUpdate, Notification
from app.schemas.responses import PaginationInfo


async def create_company_notification(db: AsyncSession, notification: NotificationCreate) -> Notification:
    """Create a new notification"""
    db_notification = CompanyNotifications(**notification.model_dump())
    db.add(db_notification)
    await db.commit()
    await db.refresh(db_notification)
    return db_notification


async def get_notification(db: AsyncSession, notification_id: UUID4) -> Optional[CompanyNotifications]:
    """Get a notification by ID"""
    stmt = select(CompanyNotifications).filter(CompanyNotifications.id == notification_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_notifications(
    db: AsyncSession,
    company_id: UUID4,
    page: int = 1, 
    per_page: int = 20,
    status_filter=None
) -> tuple[List[Notification], PaginationInfo]:
    """Get paginated notifications for a user"""
    if status_filter is None:
        status_filter = ['unread', 'read']

    stmt = select(CompanyNotifications).filter(CompanyNotifications.company_id == company_id)

    # Apply status filter if provided
    if status_filter:
        stmt = stmt.filter(CompanyNotifications.status.in_(status_filter))

    # Order by created_at descending (newest first)
    stmt = stmt.order_by(CompanyNotifications.created_at.desc())

    # Calculate total count
    count_stmt = select(func.count()).select_from(CompanyNotifications).filter(
        CompanyNotifications.company_id == company_id
    )
    if status_filter:
        count_stmt = count_stmt.filter(CompanyNotifications.status.in_(status_filter))

    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    # Calculate pagination
    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)

    result = await db.execute(stmt)
    notifications = result.scalars().all()

    total_pages = (total + per_page - 1) // per_page
    
    pagination_info = PaginationInfo(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )
    
    return notifications, pagination_info


async def update_notification(
    db: AsyncSession,
    notification_id: UUID4,
    notification_update: NotificationUpdate
) -> Optional[CompanyNotifications]:
    """Update a notification"""
    stmt = select(CompanyNotifications).filter(CompanyNotifications.id == notification_id)
    result = await db.execute(stmt)
    db_notification = result.scalar_one_or_none()

    if db_notification:
        update_data = notification_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_notification, key, value)
        await db.commit()
        await db.refresh(db_notification)
    return db_notification


async def delete_notification(db: AsyncSession, notification_id: UUID4) -> bool:
    """Delete a notification"""
    stmt = (
        update(CompanyNotifications)
        .where(CompanyNotifications.id == notification_id)
        .values(status=NotificationStatus.ARCHIVED)
    )
    await db.execute(stmt)
    await db.commit()
    return True


async def mark_notifications_as_read(db: AsyncSession, company_id: UUID4, notification_ids: List[str]) -> int:
    """Mark multiple notifications as read"""
    stmt = (
        update(CompanyNotifications)
        .where(
            and_(
                CompanyNotifications.company_id == company_id,
                CompanyNotifications.id.in_(notification_ids)
            )
        )
        .values(status=NotificationStatus.READ)
    )

    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def mark_all_notifications_as_read(db: AsyncSession, company_id: UUID4) -> int:
    """Mark all notifications as read for a user"""
    from app.models.enums import NotificationStatus
    
    stmt = (
        update(CompanyNotifications)
        .where(
            and_(
                CompanyNotifications.company_id == company_id,
                CompanyNotifications.status == NotificationStatus.UNREAD
            )
        )
        .values(status=NotificationStatus.READ)
    )

    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def get_unread_count(db: AsyncSession, company_id: UUID4) -> int:
    """Get count of unread notifications for a user"""
    from app.models.enums import NotificationStatus
    
    stmt = select(func.count(CompanyNotifications.id)).filter(
        and_(
            CompanyNotifications.company_id == company_id,
            CompanyNotifications.status == NotificationStatus.UNREAD
        )
    )
    result = await db.execute(stmt)
    return result.scalar()


async def get_all_count(db: AsyncSession, company_id: UUID4) -> int:
    """Get count of all notifications for a company"""
    stmt = select(func.count(CompanyNotifications.id)).filter(
        CompanyNotifications.company_id == company_id
    )
    result = await db.execute(stmt)
    return result.scalar()

