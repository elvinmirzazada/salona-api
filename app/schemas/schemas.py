from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.enums import GenderType, StatusType, PriceType, SourceType, AppointmentStatus


# Base schemas
class TimestampedModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    created_at: datetime
    updated_at: datetime


# Professional schemas
class ProfessionalBase(BaseModel):
    first_name: str
    last_name: str
    mobile_number: str
    country: str
    accept_privacy_policy: bool


class ProfessionalCreate(ProfessionalBase):
    password: str


class ProfessionalUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile_number: Optional[str] = None
    country: Optional[str] = None


class Professional(ProfessionalBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int


# Business schemas
class BusinessBase(BaseModel):
    business_name: str
    business_type: str
    email: EmailStr
    phone: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    team_size: Optional[int] = 0
    status: StatusType = StatusType.active


class BusinessCreate(BusinessBase):
    owner_id: int = None


class BusinessUpdate(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    team_size: Optional[int] = None
    status: Optional[StatusType] = None


class Business(BusinessBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    owner_id: int


# Staff schemas
class BusinessStaffBase(BaseModel):
    is_active: bool = False

class BusinessStaffCreate(BusinessStaffBase):
    business_id: int
    professional_id: int = None

class BusinessStaff(BusinessStaffBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    business_id: int
    professional_id: int


# Category schemas
class CategoryBase(BaseModel):
    name: str
    icon_name: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon_name: Optional[str] = None


class Category(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime


# Business Category schemas
class BusinessCategoryBase(BaseModel):
    business_id: int
    category_id: int
    is_primary: bool = False


class BusinessCategoryCreate(BusinessCategoryBase):
    pass


class BusinessCategory(BusinessCategoryBase):
    model_config = ConfigDict(from_attributes=True)
    
    created_at: datetime


# Service Type schemas
class ServiceTypeBase(BaseModel):
    name: str
    parent_type_id: Optional[int] = None
    business_id: int


class ServiceTypeCreate(ServiceTypeBase):
    pass


class ServiceTypeUpdate(BaseModel):
    name: Optional[str] = None
    parent_type_id: Optional[int] = None


class ServiceType(ServiceTypeBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int


# Service Category schemas
class ServiceCategoryBase(BaseModel):
    name: str
    color: Optional[str] = None
    description: Optional[str] = None
    business_id: int


class ServiceCategoryCreate(ServiceCategoryBase):
    pass


class ServiceCategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None


class ServiceCategory(ServiceCategoryBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int


# Service schemas
class ServiceBase(BaseModel):
    service_name: str
    service_type_id: Optional[int] = None
    service_category_id: Optional[int] = None
    description: Optional[str] = None
    price_type: PriceType = PriceType.FIXED
    price_amount: int  # Store in cents/minimal currency unit
    duration: int  # Duration in seconds
    business_id: int


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    service_name: Optional[str] = None
    service_type_id: Optional[int] = None
    service_category_id: Optional[int] = None
    description: Optional[str] = None
    price_type: Optional[PriceType] = None
    price_amount: Optional[int] = None
    duration: Optional[int] = None


class Service(ServiceBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int


# Customer schemas
class CustomerBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str


class CustomerCreate(CustomerBase):
    password: str


class CustomerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    birthdate: Optional[date] = None
    gender: Optional[GenderType] = None
    preferred_language: Optional[str] = None
    source: Optional[SourceType] = None


class Customer(CustomerBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: StatusType
    created_at: datetime


# Appointment schemas
class AppointmentBase(BaseModel):
    service_id: int
    business_id: int
    client_id: int
    start_time: datetime
    end_time: datetime
    status: str = "scheduled"


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    service_id: Optional[int] = None
    client_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None


class Appointment(AppointmentBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int


# Enhanced schemas with relationships
class BusinessWithDetails(Business):
    owner: Optional[Professional] = None
    categories: List[BusinessCategory] = []


class ServiceWithDetails(Service):
    service_type: Optional[ServiceType] = None
    service_category: Optional[ServiceCategory] = None


class AppointmentWithDetails(Appointment):
    service: Optional[Service] = None
    client: Optional[Customer] = None
    

class ResponseMessage(BaseModel):
    message: str
    status: str = "success"
