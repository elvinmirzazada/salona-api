from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import UUID4
import uuid
import logging

from app.models.models import TelegramIntegrations
from app.models.enums import StatusType
from app.schemas.schemas import TelegramIntegrationCreate, TelegramIntegrationUpdate
from app.core.encryption import encrypt_token, decrypt_token

logger = logging.getLogger(__name__)


def get_telegram_integration(db: Session, company_id: UUID4) -> Optional[TelegramIntegrations]:
    """Get active telegram integration for a company"""
    try:
        integration = db.query(TelegramIntegrations).filter(
            TelegramIntegrations.company_id == company_id,
            TelegramIntegrations.status == StatusType.active
        ).first()

        # Decrypt the bot token if integration exists
        if integration and integration.bot_token_encrypted:
            try:
                integration.bot_token = decrypt_token(integration.bot_token_encrypted)
            except Exception as e:
                logger.error(f"Failed to decrypt bot token for company {company_id}: {str(e)}")
                # Return integration without decrypted token
                integration.bot_token = None

        return integration
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching telegram integration: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching telegram integration: {str(e)}")
        raise


def get_telegram_integration_by_id(db: Session, integration_id: UUID4) -> Optional[TelegramIntegrations]:
    """Get telegram integration by ID"""
    try:
        integration = db.query(TelegramIntegrations).filter(
            TelegramIntegrations.id == integration_id
        ).first()

        # Decrypt the bot token if integration exists
        if integration and integration.bot_token_encrypted:
            try:
                integration.bot_token = decrypt_token(integration.bot_token_encrypted)
            except Exception as e:
                logger.error(f"Failed to decrypt bot token for integration {integration_id}: {str(e)}")
                # Return integration without decrypted token
                integration.bot_token = None

        return integration
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching telegram integration by ID: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching telegram integration by ID: {str(e)}")
        raise


def create_telegram_integration(
    db: Session,
    company_id: UUID4,
    integration_in: TelegramIntegrationCreate
) -> TelegramIntegrations:
    """Create a new telegram integration for a company"""
    try:
        # Check if there's an existing active integration
        existing = db.query(TelegramIntegrations).filter(
            TelegramIntegrations.company_id == company_id,
            TelegramIntegrations.status == StatusType.active
        ).first()

        if existing:
            # Deactivate the existing one
            existing.status = StatusType.inactive
            db.add(existing)

        # Encrypt the bot token before saving
        try:
            bot_token_encrypted = encrypt_token(integration_in.bot_token)
        except Exception as e:
            logger.error(f"Failed to encrypt bot token: {str(e)}")
            raise ValueError(f"Failed to encrypt bot token: {str(e)}")

        # Create new integration
        db_integration = TelegramIntegrations(
            id=uuid.uuid4(),
            company_id=company_id,
            bot_token_encrypted=bot_token_encrypted,
            chat_id=integration_in.chat_id,
            status=integration_in.status
        )

        db.add(db_integration)
        db.commit()
        db.refresh(db_integration)

        # Add decrypted token to the response object
        db_integration.bot_token = integration_in.bot_token

        return db_integration
    except SQLAlchemyError as e:
        logger.error(f"Database error while creating telegram integration: {str(e)}")
        db.rollback()
        raise
    except ValueError as e:
        logger.error(f"Validation error while creating telegram integration: {str(e)}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error while creating telegram integration: {str(e)}")
        db.rollback()
        raise


def update_telegram_integration(
    db: Session,
    integration_id: UUID4,
    integration_in: TelegramIntegrationUpdate
) -> Optional[TelegramIntegrations]:
    """Update a telegram integration"""
    try:
        db_integration = db.query(TelegramIntegrations).filter(
            TelegramIntegrations.id == integration_id
        ).first()

        if not db_integration:
            return None

        update_data = integration_in.model_dump(exclude_unset=True)

        # Encrypt the bot token if it's being updated
        if 'bot_token' in update_data and update_data['bot_token']:
            try:
                update_data['bot_token_encrypted'] = encrypt_token(update_data['bot_token'])
                decrypted_token = update_data['bot_token']
                del update_data['bot_token']
            except Exception as e:
                logger.error(f"Failed to encrypt bot token during update: {str(e)}")
                raise ValueError(f"Failed to encrypt bot token: {str(e)}")
        else:
            decrypted_token = None

        for field, value in update_data.items():
            setattr(db_integration, field, value)

        db.add(db_integration)
        db.commit()
        db.refresh(db_integration)

        # Add decrypted token to the response object
        if decrypted_token:
            db_integration.bot_token = decrypted_token
        else:
            try:
                db_integration.bot_token = decrypt_token(db_integration.bot_token_encrypted)
            except Exception as e:
                logger.error(f"Failed to decrypt bot token after update: {str(e)}")
                db_integration.bot_token = None

        return db_integration
    except SQLAlchemyError as e:
        logger.error(f"Database error while updating telegram integration: {str(e)}")
        db.rollback()
        raise
    except ValueError as e:
        logger.error(f"Validation error while updating telegram integration: {str(e)}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error while updating telegram integration: {str(e)}")
        db.rollback()
        raise


def delete_telegram_integration(db: Session, integration_id: UUID4) -> bool:
    """Delete (deactivate) a telegram integration"""
    try:
        db_integration = db.query(TelegramIntegrations).filter(
            TelegramIntegrations.id == integration_id
        ).first()

        if not db_integration:
            return False

        db_integration.status = StatusType.inactive
        db.add(db_integration)
        db.commit()

        return True
    except SQLAlchemyError as e:
        logger.error(f"Database error while deleting telegram integration: {str(e)}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error while deleting telegram integration: {str(e)}")
        db.rollback()
        raise
