from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, UUID4

from app.models import CustomerStatusType
from app.models.enums import GenderType, StatusType, PriceType, SourceType, AppointmentStatus


# Base schemas
class TimestampedModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    created_at: datetime
    updated_at: datetime


# Users schemas
class UserBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile_number: Optional[str] = None
    country: Optional[str] = None


class User(UserBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    status: CustomerStatusType


# class CompanyUser(BaseModel):
#     id: str
#     user_id: str
#     company_id: str



# Company schemas
class CompanyBase(BaseModel):
    name: str
    type: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    team_size: Optional[int] = 0
    status: StatusType = StatusType.inactive


class CompanyCreate(CompanyBase):
    pass


class Company(CompanyBase, TimestampedModel):
    id: UUID4

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)



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
    
    id: str
    status: CustomerStatusType
    created_at: datetime

#
# # Appointment schemas
# class AppointmentBase(BaseModel):
#     service_id: int
#     business_id: int
#     client_id: int
#     start_time: datetime
#     end_time: datetime
#     status: str = "scheduled"
#
#
# class AppointmentCreate(AppointmentBase):
#     pass
#
#
# class AppointmentUpdate(BaseModel):
#     service_id: Optional[int] = None
#     client_id: Optional[int] = None
#     start_time: Optional[datetime] = None
#     end_time: Optional[datetime] = None
#     status: Optional[str] = None
#
#
# class Appointment(AppointmentBase, TimestampedModel):
#     model_config = ConfigDict(from_attributes=True)
#
#     id: int
#

# # Enhanced schemas with relationships
# class BusinessWithDetails(Business):
#     owner: Optional[User] = None
#     categories: List[BusinessCategory] = []
#
#
# class ServiceWithDetails(Service):
#     service_type: Optional[ServiceType] = None
#     service_category: Optional[ServiceCategory] = None
#
#
# class AppointmentWithDetails(Appointment):
#     service: Optional[Service] = None
#     client: Optional[Customer] = None
#

class ResponseMessage(BaseModel):
    message: str
    status: str = "success"
