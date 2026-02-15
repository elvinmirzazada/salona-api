import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.models.enums import NotificationType
from app.schemas import NotificationCreate
from app.schemas.schemas import CompanyNotificationCreate
from app.services.crud import notification as crud_notification

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        pass

    @staticmethod
    async def create_notification(
            db: AsyncSession,
            notification_request: NotificationCreate
    ) -> bool:
        """
        Create a notification by calling the notification CRUD function directly

        Args:
            db: Database session
            notification_request

        Returns:
            bool: True if notification was created successfully, False otherwise
        """
        try:
            
            notification = await crud_notification.create_company_notification(db=db, notification=notification_request)
            if notification:
                return True
        except Exception as e:
            logger.error(f"Unexpected error while creating notification: {e}")
            return False



# Global instance
notification_service = NotificationService()
