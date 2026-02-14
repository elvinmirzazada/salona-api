import uuid

from pydantic.v1 import create_model_from_typeddict
from sqlalchemy import (Column, Integer, String, Boolean, DateTime, Text, Date, ForeignKey, UniqueConstraint, UUID,
                        Time, Computed,
                        CheckConstraint, false, BLOB, LargeBinary, Index, select)
from sqlalchemy.dialects.postgresql import ENUM as SQLAlchemyEnum
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.sql import func
from sqlalchemy.sql import expression
from sqlalchemy.ext.hybrid import hybrid_property

from app.db.base_class import BaseModel
from app.models.enums import (StatusType, BookingStatus, CustomerStatusType, EmailStatusType,
                              PhoneStatusType, VerificationType, VerificationStatus,
                              CompanyRoleType, NotificationType, NotificationStatus, MembershipPlanType, InvitationStatus)
from app.core.datetime_utils import utcnow


#
class Users(BaseModel):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    status = Column(SQLAlchemyEnum(CustomerStatusType), default=CustomerStatusType.pending_verification)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    languages = Column(String(255), nullable=True)
    position = Column(String(255), nullable=True)
    profile_photo_url = Column(String(510), nullable=True)

    company_user = relationship("CompanyUsers", back_populates="user")
    user_time_offs = relationship("UserTimeOffs", back_populates="user")
    booked_services = relationship("BookingServices", back_populates="assigned_staff")


class UserVerifications(BaseModel):
    __tablename__ = "user_verifications"

    id = Column(UUID, primary_key=True, index=True)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"))
    token = Column(String(255), nullable=False, unique=True)
    type = Column(SQLAlchemyEnum(VerificationType), nullable=False)
    status = Column(SQLAlchemyEnum(VerificationStatus), default=VerificationStatus.PENDING)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    used_at = Column(DateTime(timezone=True), nullable=True)


class UserAvailabilities(BaseModel):
    __tablename__ = "user_availabilities"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True, unique=True)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"))
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(Time, nullable=False)  # Store only time (HH:MM)
    end_time = Column(Time, nullable=False)    # Store only time (HH:MM)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        # Add constraint to ensure start_time is before end_time
        CheckConstraint('start_time < end_time', name='check_time_order'),
        # Add unique constraint to prevent overlapping time slots for the same user and day
        UniqueConstraint('user_id', 'day_of_week', 'start_time', 'end_time', name='unique_user_availability')
    )


class UserTimeOffs(BaseModel):
    __tablename__ = "user_time_offs"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True, unique=True)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"))
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("Users", back_populates="user_time_offs", lazy="selectin")


class Companies(BaseModel):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)
    logo_url = Column(String(255))
    website = Column(String(255))
    description = Column(Text)
    team_size = Column(Integer, default=1)
    timezone = Column(String(100), default='UTC')
    status = Column(SQLAlchemyEnum(StatusType), default=StatusType.active)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    slug = Column(
        String,
        Computed("REPLACE(LOWER(name), ' ', '-')", persisted=True)
    )

    invitations = relationship("Invitations", back_populates="company")


class CompanyEmails(BaseModel):
    __tablename__ = "company_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    email = Column(String(255), nullable=False, unique=True)
    status = Column(SQLAlchemyEnum(EmailStatusType), default=EmailStatusType.unverified)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class CompanyPhones(BaseModel):
    __tablename__ = "company_phones"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    phone = Column(String(20), nullable=False)
    is_primary = Column(Boolean, default=False)
    status = Column(SQLAlchemyEnum(PhoneStatusType), default=PhoneStatusType.unverified)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class CompanyAddresses(BaseModel):
    __tablename__ = "company_addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    zip = Column(String(20))
    country = Column(String(100), nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CompanyUsers(BaseModel):
    __tablename__ = "company_users"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"))
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    role = Column(SQLAlchemyEnum(CompanyRoleType), default=CompanyRoleType.viewer)  # e.g., admin, member
    status = Column(SQLAlchemyEnum(StatusType), default=StatusType.inactive)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("Users", back_populates="company_user")

    __table_args__ = (UniqueConstraint('user_id', 'company_id', name='_user_company_uc'),)


class Customers(BaseModel):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    status = Column(SQLAlchemyEnum(CustomerStatusType), default=CustomerStatusType.pending_verification)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    booking = relationship("Bookings", back_populates="customer")

class CustomerEmails(BaseModel):
    __tablename__ = "customer_emails"

    id = Column(UUID, primary_key=True, index=True)
    customer_id = Column(UUID, ForeignKey("customers.id", ondelete="CASCADE"))
    email = Column(String(255), nullable=False, unique=True)
    status = Column(SQLAlchemyEnum(EmailStatusType), default=EmailStatusType.unverified)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class CustomerPhones(BaseModel):
    __tablename__ = "customer_phones"

    id = Column(UUID, primary_key=True, index=True)
    customer_id = Column(UUID, ForeignKey("customers.id", ondelete="CASCADE"))
    phone = Column(String(20), nullable=False)
    is_primary = Column(Boolean, default=False)
    status = Column(SQLAlchemyEnum(PhoneStatusType), default=PhoneStatusType.unverified)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class CustomerAddresses(BaseModel):
    __tablename__ = "customer_addresses"

    id = Column(UUID, primary_key=True, index=True)
    customer_id = Column(UUID, ForeignKey("customers.id", ondelete="CASCADE"))
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255))
    city = Column(String(100), nullable=False)
    zip = Column(String(20))
    country = Column(String(100), nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class CustomerVerifications(BaseModel):
    __tablename__ = "customer_verifications"

    id = Column(UUID, primary_key=True, index=True)
    customer_id = Column(UUID, ForeignKey("customers.id", ondelete="CASCADE"))
    token = Column(String(255), nullable=False, unique=True)
    type = Column(SQLAlchemyEnum(VerificationType), nullable=False)
    status = Column(SQLAlchemyEnum(VerificationStatus), default=VerificationStatus.PENDING)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    used_at = Column(DateTime(timezone=True), nullable=True)

class Bookings(BaseModel):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True, unique=True)
    customer_id = Column(UUID, ForeignKey("customers.id", ondelete="CASCADE"), nullable=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    status = Column(SQLAlchemyEnum(BookingStatus), default=BookingStatus.SCHEDULED)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    total_price = Column(Integer, nullable=False)
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    customer = relationship("Customers", back_populates="booking")
    booking_services = relationship("BookingServices", back_populates="booking")


class CompanyCategories(BaseModel):
    __tablename__ = "company_categories"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True, unique=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    parent_category_id = Column(UUID(as_uuid=True), ForeignKey("company_categories.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=True)
    name_ee = Column(String(100), nullable=True)
    name_ru = Column(String(100), nullable=True)
    description = Column(Text)
    description_en = Column(Text, nullable=True)
    description_ee = Column(Text, nullable=True)
    description_ru = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    category_service = relationship("CategoryServices", back_populates="company_category", lazy='selectin')
    subcategories = relationship("CompanyCategories",
                                  backref="parent",
                                  remote_side=[id],
                                  cascade="all, delete", lazy='selectin')

    @hybrid_property
    def services_count(self):
        """Return the count of services in this category"""
        if self.category_service is None:
            return 0
        try:
            return len(self.category_service)
        except (TypeError, AttributeError):
            return 0

    @hybrid_property
    def has_subcategories(self):
        """Check if this category has subcategories"""
        if self.subcategories is None:
            return False
        try:
            return len(self.subcategories) > 0
        except (TypeError, AttributeError):
            return False


class CategoryServices(BaseModel):
    __tablename__ = "category_services"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True, unique=True)
    category_id = Column(UUID, ForeignKey("company_categories.id", ondelete="CASCADE"))
    name = Column(String(255))
    name_en = Column(String(255), nullable=True)
    name_ee = Column(String(255), nullable=True)
    name_ru = Column(String(255), nullable=True)
    duration = Column(Integer)
    price = Column(Integer)
    discount_price = Column(Integer)
    additional_info = Column(Text)
    additional_info_en = Column(Text, nullable=True)
    additional_info_ee = Column(Text, nullable=True)
    additional_info_ru = Column(Text, nullable=True)
    status = Column(SQLAlchemyEnum(StatusType), default=StatusType.active)
    buffer_before = Column(Integer, default=0)  # in minutes
    buffer_after = Column(Integer, default=0)   # in minutes
    image_url = Column(String(510), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    company_category = relationship("CompanyCategories", back_populates="category_service")
    # booking_category_services = relationship("BookingServices", back_populates="category_service")
    service_staff = relationship("ServiceStaff", back_populates="service")


class ServiceStaff(BaseModel):
    __tablename__ = "service_staff"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    service_id = Column(UUID, ForeignKey("category_services.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    service = relationship("CategoryServices", back_populates="service_staff")
    user = relationship("Users")

    __table_args__ = (
        UniqueConstraint('service_id', 'user_id', name='_service_user_uc'),
    )


class BookingServices(BaseModel):
    __tablename__ = "booking_services"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True, unique=True)
    booking_id = Column(UUID, ForeignKey("bookings.id", ondelete="CASCADE"))
    category_service_id = Column(UUID, ForeignKey("category_services.id", ondelete="CASCADE"))
    user_id = Column(UUID, ForeignKey("users.id", ondelete="SET NULL"))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)

    booking = relationship("Bookings", back_populates="booking_services")
    # category_service = relationship("CategoryServices", back_populates="booking_category_services")
    assigned_staff = relationship("Users", back_populates="booked_services")



class CompanyNotifications(BaseModel):
    __tablename__ = "company_notifications"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    type = Column(SQLAlchemyEnum(NotificationType), nullable=False)
    status = Column(SQLAlchemyEnum(NotificationStatus), default=NotificationStatus.UNREAD)
    message = Column(Text, nullable=False)
    data = Column(LargeBinary, nullable=True)  # JSON or additional data
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MembershipPlans(BaseModel):
    __tablename__ = "membership_plans"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    plan_type = Column(SQLAlchemyEnum(MembershipPlanType), nullable=False, unique=True)
    description = Column(Text)
    url = Column(Text)
    price = Column(Integer, nullable=False)  # Price in cents
    duration_days = Column(Integer, nullable=False, default=30)  # Subscription duration
    status = Column(SQLAlchemyEnum(StatusType), default=StatusType.active)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    subscriptions = relationship("CompanyMemberships", back_populates="membership_plan")


class CompanyMemberships(BaseModel):
    __tablename__ = "company_memberships"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    membership_plan_id = Column(UUID, ForeignKey("membership_plans.id", ondelete="CASCADE"), nullable=False)
    status = Column(SQLAlchemyEnum(StatusType), default=StatusType.active)
    start_date = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    end_date = Column(DateTime(timezone=True), nullable=False)
    auto_renew = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    membership_plan = relationship("MembershipPlans", back_populates="subscriptions")

    __table_args__ = (
        # Ensure a company can only have one active membership at a time
        Index(
            'unique_active_company_membership',
            'company_id',
            unique=True,
            postgresql_where=(expression.text("status = 'active'"))
        ),
    )


class TelegramIntegrations(BaseModel):
    __tablename__ = "telegram_integrations"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    bot_token_encrypted = Column(String(255), nullable=False)
    chat_id = Column(String(255), nullable=True)
    status = Column(SQLAlchemyEnum(StatusType), default=StatusType.active)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        # Ensure a company can only have one active telegram integration
        Index(
            'unique_active_telegram_integration',
            'company_id',
            unique=True,
            postgresql_where=(expression.text("status = 'active'"))
        ),
    )


class Invitations(BaseModel):
    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    token = Column(String(255), nullable=False, unique=True)
    role = Column(SQLAlchemyEnum(CompanyRoleType), default=CompanyRoleType.viewer)
    status = Column(SQLAlchemyEnum(InvitationStatus), default=InvitationStatus.PENDING)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    company = relationship("Companies", back_populates="invitations")

    __table_args__ = (UniqueConstraint('email', 'company_id', name='_email_company_uc'),)