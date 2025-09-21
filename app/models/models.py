import uuid

from sqlalchemy import (Column, Integer, String, Boolean, DateTime, Text, Date, ForeignKey, UniqueConstraint, UUID,
                        Time,
                        CheckConstraint)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.sql import func

from app.db.base_class import BaseModel
from app.models.enums import (StatusType, BookingStatus, CustomerStatusType, EmailStatusType,
                              PhoneStatusType, VerificationType, VerificationStatus,
                              CompanyRoleType)


#
class Users(BaseModel):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    status = Column(SQLAlchemyEnum(CustomerStatusType), default=CustomerStatusType.pending_verification)
    email_verified = Column(Boolean, default=False)


class UserAvailabilities(BaseModel):
    __tablename__ = "user_availabilities"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True, unique=True)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"))
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(Time, nullable=False)  # Store only time (HH:MM)
    end_time = Column(Time, nullable=False)    # Store only time (HH:MM)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

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
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Companies(BaseModel):
    __tablename__ = "companies"

    id = Column(UUID, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)
    logo_url = Column(String(255))
    website = Column(String(255))
    description = Column(Text)
    team_size = Column(Integer, default=1)
    status = Column(SQLAlchemyEnum(StatusType), default=StatusType.active)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class CompanyEmails(BaseModel):
    __tablename__ = "company_emails"

    id = Column(UUID, primary_key=True, index=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    email = Column(String(255), nullable=False, unique=True)
    status = Column(SQLAlchemyEnum(EmailStatusType), default=EmailStatusType.unverified)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class CompanyPhones(BaseModel):
    __tablename__ = "company_phones"

    id = Column(UUID, primary_key=True, index=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    phone = Column(String(20), nullable=False)
    is_primary = Column(Boolean, default=False)
    status = Column(SQLAlchemyEnum(PhoneStatusType), default=PhoneStatusType.unverified)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class CompanyAddresses(BaseModel):
    __tablename__ = "company_addresses"

    id = Column(UUID, primary_key=True, index=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    zip = Column(String(20))
    country = Column(String(100), nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class CompanyUsers(BaseModel):
    __tablename__ = "company_users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"))
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    role = Column(SQLAlchemyEnum(CompanyRoleType), default=CompanyRoleType.viewer)  # e.g., admin, member
    status = Column(SQLAlchemyEnum(StatusType), default=StatusType.inactive)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint('user_id', 'company_id', name='_user_company_uc'),)

#
#     # Relationships
#     owner = relationship("Professional", back_populates="businesses")
#     # categories = relationship("BusinessCategory", back_populates="business")
#     service_types = relationship("ServiceType", back_populates="business")
#     service_categories = relationship("ServiceCategory", back_populates="business")
#     services = relationship("Service", back_populates="business")
#     clients = relationship("Client", back_populates="business")
#     appointments = relationship("Appointment", back_populates="business")
#     staff = relationship("BusinessStaff", back_populates="business")
#
# # class BusinessStaff(BaseModel):
# #     __tablename__ = "business_staff"
# #
# #     id = Column(Integer, primary_key=True, index=True)
# #     business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
# #     professional_id = Column(Integer, ForeignKey("professionals.id", ondelete="CASCADE"))
# #     is_active = Column(Boolean, default=True)
# #
# #     # Relationships
# #     business = relationship("Business", back_populates="staff")
# #     professional = relationship("Professional")
#
#
# class Category(BaseModel):
#     __tablename__ = "categories"
#
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100), nullable=False)
#     icon_name = Column(String(50))
#     created_at = Column(DateTime, default=func.now())
#
#     # Relationships
#     # businesses = relationship("BusinessCategory", back_populates="category")
#
#
# # class BusinessCategory(BaseModel):
# #     __tablename__ = "business_categories"
#
# #     business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True)
# #     category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)
# #     is_primary = Column(Boolean, default=False)
# #     created_at = Column(DateTime, default=func.now())
#
# #     # Relationships
# #     business = relationship("Business", back_populates="categories")
# #     category = relationship("Category", back_populates="businesses")
#
#
# class ServiceType(BaseModel):
#     __tablename__ = "service_types"
#
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100), nullable=False)
#     parent_type_id = Column(Integer, ForeignKey("service_types.id", ondelete="SET NULL"))
#     business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
#
#     # Relationships
#     parent = relationship("ServiceType", remote_side=[id])
#     business = relationship("Business", back_populates="service_types")
#     services = relationship("Service", back_populates="service_type")
#
#
# class ServiceCategory(BaseModel):
#     __tablename__ = "service_categories"
#
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100), nullable=False)
#     color = Column(String(7))  # Hex color code
#     description = Column(Text)
#     business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
#
#     # Relationships
#     business = relationship("Business", back_populates="service_categories")
#     services = relationship("Service", back_populates="service_category")
#
#


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
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class CustomerEmails(BaseModel):
    __tablename__ = "customer_emails"

    id = Column(UUID, primary_key=True, index=True)
    customer_id = Column(UUID, ForeignKey("customers.id", ondelete="CASCADE"))
    email = Column(String(255), nullable=False, unique=True)
    status = Column(SQLAlchemyEnum(EmailStatusType), default=EmailStatusType.unverified)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class CustomerPhones(BaseModel):
    __tablename__ = "customer_phones"

    id = Column(UUID, primary_key=True, index=True)
    customer_id = Column(UUID, ForeignKey("customers.id", ondelete="CASCADE"))
    phone = Column(String(20), nullable=False)
    is_primary = Column(Boolean, default=False)
    status = Column(SQLAlchemyEnum(PhoneStatusType), default=PhoneStatusType.unverified)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

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
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class CustomerVerifications(BaseModel):
    __tablename__ = "customer_verifications"

    id = Column(UUID, primary_key=True, index=True)
    customer_id = Column(UUID, ForeignKey("customers.id", ondelete="CASCADE"))
    token = Column(String(255), nullable=False, unique=True)
    type = Column(SQLAlchemyEnum(VerificationType), nullable=False)
    status = Column(SQLAlchemyEnum(VerificationStatus), default=VerificationStatus.PENDING)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    used_at = Column(DateTime, nullable=True)

class Bookings(BaseModel):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True, unique=True)
    customer_id = Column(UUID, ForeignKey("customers.id", ondelete="CASCADE"), nullable=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    status = Column(SQLAlchemyEnum(BookingStatus), default=BookingStatus.SCHEDULED)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    total_price = Column(Integer, nullable=False)
    notes = Column(Text)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class GeneralServices(BaseModel):
    __tablename__ = "general_services"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True, unique=True)
    name = Column(String(255), nullable=False)
    default_duration = Column(Integer, nullable=False)
    default_price = Column(Integer, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class CompanyServices(BaseModel):
    __tablename__ = "company_services"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True, unique=True)
    company_id = Column(UUID, ForeignKey("companies.id", ondelete="CASCADE"))
    general_service_id = Column(UUID, ForeignKey("general_services.id", ondelete="CASCADE"))
    custom_name = Column(String(255))
    custom_duration = Column(Integer)
    custom_price = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class BookingServices(BaseModel):
    __tablename__ = "booking_services"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True, unique=True)
    booking_id = Column(UUID, ForeignKey("bookings.id", ondelete="CASCADE"))
    company_service_id = Column(UUID, ForeignKey("company_services.id", ondelete="CASCADE"))
    user_id = Column(UUID, ForeignKey("users.id", ondelete="SET NULL"))
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
