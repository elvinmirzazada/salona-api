import uuid
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.models import Invitations, CompanyUsers
from app.schemas.schemas import Invitation
from app.models.enums import InvitationStatus, StatusType, CompanyRoleType
from app.core.datetime_utils import utcnow
import logging

logger = logging.getLogger(__name__)


def create_invitation(
    db: Session,
    company_id: str,
    email: str,
    role: CompanyRoleType = CompanyRoleType.staff,
    token: str = None
) -> Invitation:
    """
    Create a new invitation for a staff member.

    Args:
        db: Database session
        company_id: Company ID
        email: Email to invite
        role: Role to assign (default: staff)
        token: Invitation token (if not provided, one will be generated)

    Returns:
        Invitations: The created invitation record
    """
    try:
        if not token:
            token = str(uuid.uuid4())

        # Check if an active invitation already exists for this email and company
        existing = db.query(Invitations).filter(
            Invitations.email == email,
            Invitations.company_id == company_id,
            Invitations.status == InvitationStatus.PENDING
        ).first()

        if existing:
            # Update the existing invitation
            existing.token = token
            existing.role = role
            existing.updated_at = utcnow()
            db.add(existing)
            db.commit()
            db.refresh(existing)

            return Invitation.model_validate(existing)

        # Create new invitation
        invitation = Invitations(
            id=str(uuid.uuid4()),
            email=email,
            token=token,
            role=role,
            company_id=company_id,
            status=InvitationStatus.PENDING
        )
        
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        return Invitation.model_validate(invitation)

    except SQLAlchemyError as e:
        logger.error(f"Database error creating invitation: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating invitation: {e}")
        db.rollback()
        raise


def get_invitation_by_token(db: Session, token: str) -> Optional[Invitations]:
    """
    Get an invitation by token.

    Args:
        db: Database session
        token: Invitation token

    Returns:
        Invitations: The invitation record or None if not found
    """
    try:
        invitation = db.query(Invitations).filter(
            Invitations.token == token,
            Invitations.status == InvitationStatus.PENDING
        ).first()

        # Check if invitation has expired (older than 3 days)
        if invitation:
            expires_at = invitation.created_at + timedelta(days=3)
            if datetime.now(timezone.utc) > expires_at:
                invitation.status = InvitationStatus.EXPIRED
                db.add(invitation)
                db.commit()
                db.refresh(invitation)
                return None

        return invitation
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching invitation: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching invitation: {str(e)}")
        raise


def get_invitation_by_email_and_company(
    db: Session,
    email: str,
    company_id: UUID4
) -> Optional[Invitations]:
    """
    Get an invitation by email and company.

    Args:
        db: Database session
        email: Email address
        company_id: Company ID

    Returns:
        Invitations: The invitation record or None if not found
    """
    try:
        return db.query(Invitations).filter(
            Invitations.email == email,
            Invitations.company_id == company_id
        ).first()
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching invitation: {str(e)}")
        raise


async def get_company_invitations(
    db: AsyncSession,
    company_id: str,
    status: Optional[InvitationStatus] = None
) -> List[Invitations]:
    """
    Get all invitations for a company, optionally filtered by status.

    Args:
        db: Database session
        company_id: Company ID
        status: Optional status filter

    Returns:
        List[Invitations]: List of invitation records
    """
    try:
        stmt = (select(Invitations)
                .filter(Invitations.company_id == company_id))
        if status:
            stmt = stmt.filter(Invitations.status == status)

        result = await db.execute(stmt)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching invitations: {str(e)}")
        raise


def accept_invitation(
    db: Session,
    invitation: Invitations,
    user_id: UUID4
) -> bool:
    """
    Accept an invitation and add user to company.

    Args:
        db: Database session
        invitation: Invitation record
        user_id: User ID

    Returns:
        bool: True if successful
    """
    try:
        # Update invitation status
        invitation.status = InvitationStatus.USED
        invitation.updated_at = utcnow()
        db.add(invitation)

        # Check if user is already a company member
        existing_member = db.query(CompanyUsers).filter(
            CompanyUsers.user_id == user_id,
            CompanyUsers.company_id == invitation.company_id
        ).first()

        if not existing_member:
            # Add user to company
            company_user = CompanyUsers(
                id=uuid.uuid4(),
                user_id=user_id,
                company_id=invitation.company_id,
                role=invitation.role,
                status=StatusType.active
            )
            db.add(company_user)
        else:
            # If already a member, update their role and status
            existing_member.role = invitation.role
            existing_member.status = StatusType.active
            db.add(existing_member)

        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while accepting invitation: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error while accepting invitation: {str(e)}")
        raise


def decline_invitation(db: Session, token: str) -> bool:
    """
    Decline an invitation.

    Args:
        db: Database session
        token: Invitation token

    Returns:
        bool: True if successful
    """
    try:
        invitation = db.query(Invitations).filter(
            Invitations.token == token
        ).first()

        if not invitation:
            return False

        invitation.status = InvitationStatus.DECLINED
        invitation.updated_at = utcnow()
        db.add(invitation)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while declining invitation: {str(e)}")
        raise


def resend_invitation(
    db: Session,
    company_id: UUID4,
    email: str
) -> Optional[Invitations]:
    """
    Resend an invitation by generating a new token.

    Args:
        db: Database session
        company_id: Company ID
        email: Email address

    Returns:
        Invitations: The updated invitation record or None if not found
    """
    try:
        invitation = db.query(Invitations).filter(
            Invitations.email == email,
            Invitations.company_id == company_id,
            Invitations.status.in_([InvitationStatus.PENDING, InvitationStatus.EXPIRED])
        ).first()

        if not invitation:
            return None

        # Generate new token and reset to pending
        invitation.token = str(uuid.uuid4())
        invitation.status = InvitationStatus.PENDING
        invitation.created_at = utcnow()
        invitation.updated_at = utcnow()

        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        return invitation
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while resending invitation: {str(e)}")
        raise
