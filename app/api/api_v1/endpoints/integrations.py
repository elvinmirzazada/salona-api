from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import UUID4
import logging

from app.db.session import get_db
from app.schemas.schemas import TelegramIntegration, TelegramIntegrationCreate, TelegramIntegrationUpdate
from app.schemas.responses import DataResponse
from app.services.crud import integration as crud_integration
from app.api.dependencies import get_current_company_id, require_admin_or_owner

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/telegram", response_model=DataResponse[TelegramIntegration], status_code=status.HTTP_201_CREATED)
async def create_telegram_integration(
    *,
    db: Session = Depends(get_db),
    company_id: UUID4 = Depends(get_current_company_id),
    integration_in: TelegramIntegrationCreate,
    _: None = Depends(require_admin_or_owner)
) -> DataResponse[TelegramIntegration]:
    """
    Create a new Telegram bot integration for the company.
    Bot token will be encrypted before storing.
    Only admin or owner can create integrations.
    """
    try:
        integration = crud_integration.create_telegram_integration(
            db=db,
            company_id=company_id,
            integration_in=integration_in
        )
        response = TelegramIntegration.model_validate(integration)
        return DataResponse.success_response(
            data=response,
            message="Telegram integration created successfully",
            status_code=status.HTTP_201_CREATED
        )
    except ValueError as e:
        logger.error(f"Validation error creating telegram integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error creating telegram integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while creating integration"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating telegram integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating integration"
        )


@router.get("/telegram", response_model=DataResponse[Optional[TelegramIntegration]])
async def get_telegram_integration(
    *,
    db: Session = Depends(get_db),
    company_id: UUID4 = Depends(get_current_company_id)
) -> DataResponse[Optional[TelegramIntegration]]:
    """
    Get the active Telegram integration for the current company.
    """
    try:
        integration = crud_integration.get_telegram_integration(db=db, company_id=company_id)
        if integration:
            response = TelegramIntegration.model_validate(integration)
        else:
            response = None
        return DataResponse.success_response(
            data=response,
            message="Telegram integration retrieved successfully"
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving telegram integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while retrieving integration"
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving telegram integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving integration"
        )


@router.patch("/telegram/{integration_id}", response_model=DataResponse[TelegramIntegration])
async def update_telegram_integration(
    *,
    db: Session = Depends(get_db),
    company_id: UUID4 = Depends(get_current_company_id),
    integration_id: UUID4,
    integration_in: TelegramIntegrationUpdate,
    _: None = Depends(require_admin_or_owner)
) -> DataResponse[TelegramIntegration]:
    """
    Update a Telegram integration.
    Only admin or owner can update integrations.
    """
    try:
        # Verify the integration belongs to the current company
        existing_integration = crud_integration.get_telegram_integration_by_id(db=db, integration_id=integration_id)
        if not existing_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Telegram integration not found"
            )

        if existing_integration.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        integration = crud_integration.update_telegram_integration(
            db=db,
            integration_id=integration_id,
            integration_in=integration_in
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Telegram integration not found"
            )

        response = TelegramIntegration.model_validate(integration)
        return DataResponse.success_response(
            data=response,
            message="Telegram integration updated successfully"
        )
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating telegram integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error updating telegram integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while updating integration"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating telegram integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating integration"
        )


@router.delete("/telegram/{integration_id}", response_model=DataResponse[dict])
async def delete_telegram_integration(
    *,
    db: Session = Depends(get_db),
    company_id: UUID4 = Depends(get_current_company_id),
    integration_id: UUID4,
    _: None = Depends(require_admin_or_owner)
) -> DataResponse[dict]:
    """
    Delete (deactivate) a Telegram integration.
    Only admin or owner can delete integrations.
    """
    try:
        # Verify the integration belongs to the current company
        existing_integration = crud_integration.get_telegram_integration_by_id(db=db, integration_id=integration_id)
        if not existing_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Telegram integration not found"
            )

        if existing_integration.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        success = crud_integration.delete_telegram_integration(db=db, integration_id=integration_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete Telegram integration"
            )

        return DataResponse.success_response(
            data={"deleted": True},
            message="Telegram integration deleted successfully"
        )
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting telegram integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while deleting integration"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting telegram integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting integration"
        )
