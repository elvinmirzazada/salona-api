from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLAlchemyEnum
from app.db.base_class import BaseModel
from app.models.enums import GenderType, StatusType, PriceType, SourceType, AppointmentStatus


class Professional(BaseModel):
    __tablename__ = "professionals"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    password = Column(String(255), nullable=False)
    mobile_number = Column(String(20), nullable=False, unique=True)
    country = Column(String(50), nullable=False)
    accept_privacy_policy = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    businesses = relationship("Business", back_populates="owner")


class Business(BaseModel):
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(100), nullable=False)
    business_type = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(50))
    postal_code = Column(String(20))
    country = Column(String(50))
    owner_id = Column(Integer, ForeignKey("professionals.id"))
    logo_url = Column(String(255))
    website = Column(String(255))
    description = Column(Text)
    team_size = Column(Integer, default=0)
    status = Column(SQLAlchemyEnum(StatusType), default=StatusType.active)
    
    # Relationships
    owner = relationship("Professional", back_populates="businesses")
    # categories = relationship("BusinessCategory", back_populates="business")
    service_types = relationship("ServiceType", back_populates="business")
    service_categories = relationship("ServiceCategory", back_populates="business")
    services = relationship("Service", back_populates="business")
    clients = relationship("Client", back_populates="business")
    appointments = relationship("Appointment", back_populates="business")
    staff = relationship("BusinessStaff", back_populates="business")

class BusinessStaff(BaseModel):
    __tablename__ = "business_staff"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
    professional_id = Column(Integer, ForeignKey("professionals.id", ondelete="CASCADE"))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    business = relationship("Business", back_populates="staff")
    professional = relationship("Professional")


class Category(BaseModel):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    icon_name = Column(String(50))
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    # businesses = relationship("BusinessCategory", back_populates="category")


# class BusinessCategory(BaseModel):
#     __tablename__ = "business_categories"
    
#     business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True)
#     category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)
#     is_primary = Column(Boolean, default=False)
#     created_at = Column(DateTime, default=func.now())
    
#     # Relationships
#     business = relationship("Business", back_populates="categories")
#     category = relationship("Category", back_populates="businesses")


class ServiceType(BaseModel):
    __tablename__ = "service_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    parent_type_id = Column(Integer, ForeignKey("service_types.id", ondelete="SET NULL"))
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
    
    # Relationships
    parent = relationship("ServiceType", remote_side=[id])
    business = relationship("Business", back_populates="service_types")
    services = relationship("Service", back_populates="service_type")


class ServiceCategory(BaseModel):
    __tablename__ = "service_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    color = Column(String(7))  # Hex color code
    description = Column(Text)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
    
    # Relationships
    business = relationship("Business", back_populates="service_categories")
    services = relationship("Service", back_populates="service_category")


class Service(BaseModel):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), nullable=False)
    service_type_id = Column(Integer, ForeignKey("service_types.id", ondelete="SET NULL"))
    service_category_id = Column(Integer, ForeignKey("service_categories.id", ondelete="SET NULL"))
    description = Column(Text)
    price_type = Column(SQLAlchemyEnum(PriceType), default=PriceType.FIXED)
    price_amount = Column(Integer, nullable=False)  # Store in cents/minimal currency unit
    duration = Column(Integer, nullable=False)  # Duration in seconds
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
    
    # Relationships
    service_type = relationship("ServiceType", back_populates="services")
    service_category = relationship("ServiceCategory", back_populates="services")
    business = relationship("Business", back_populates="services")
    appointments = relationship("Appointment", back_populates="service")


class Client(BaseModel):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(255))
    phone_number = Column(String(20), nullable=False)
    birthdate = Column(Date)
    gender = Column(SQLAlchemyEnum(GenderType))
    preferred_language = Column(String(10), default="en")
    source = Column(SQLAlchemyEnum(SourceType), default=SourceType.WALK_IN)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
    
    __table_args__ = (
        UniqueConstraint('phone_number', 'business_id', name='_phone_business_uc'),
    )
    
    # Relationships
    business = relationship("Business", back_populates="clients")
    appointments = relationship("Appointment", back_populates="client")


class Appointment(BaseModel):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="RESTRICT"))
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="RESTRICT"))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String(20), default="scheduled")
    
    # Relationships
    service = relationship("Service", back_populates="appointments")
    business = relationship("Business", back_populates="appointments")
    client = relationship("Client", back_populates="appointments")
