from datetime import datetime, date, time
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, UUID4

from app.models import CustomerStatusType
from app.models.enums import GenderType, StatusType, PriceType, SourceType, BookingStatus, AvailabilityType


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
    
    id: UUID4
    status: CustomerStatusType


class CompanyUser(BaseModel):
    user_id: UUID4
    company_id: UUID4
    role: str
    status: StatusType
    user: User


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
    status: CustomerStatusType = CustomerStatusType.disabled


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


# Booking schemas
class BookingBase(BaseModel):
    customer_id: UUID4
    company_id: UUID4
    start_at: datetime
    end_at: datetime
    status: BookingStatus = BookingStatus.SCHEDULED
    notes: Optional[str] = None

class GuestCustomerInfo(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str

class BookingServiceRequest(BaseModel):
    category_service_id: UUID4
    user_id: UUID4
    notes: Optional[str] = None

class BookingCreate(BaseModel):
    company_id: UUID4
    start_time: datetime
    services: List[BookingServiceRequest]
    notes: Optional[str] = None
    customer_info: Optional[GuestCustomerInfo] = None  # For unregistered customers


class BookingUpdate(BaseModel):
    service_id: Optional[int] = None
    client_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None


class Booking(BookingBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    total_price: int

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
# class BookingWithDetails(Booking):
#     service: Optional[Service] = None
#     client: Optional[Customer] = None
#

class ResponseMessage(BaseModel):
    message: str
    status: str = "success"


class TimeSlot(BaseModel):
    start_time: time
    end_time: time
    is_available: bool

class DailyAvailability(BaseModel):
    date: date
    time_slots: List[TimeSlot]

class WeeklyAvailability(BaseModel):
    week_start_date: date
    week_end_date: date
    daily_slots: List[DailyAvailability]

class MonthlyAvailability(BaseModel):
    month: int
    year: int
    weekly_slots: List[WeeklyAvailability]

class AvailabilityResponse(BaseModel):
    user_id: str
    availability_type: AvailabilityType
    daily: Optional[DailyAvailability] = None
    weekly: Optional[WeeklyAvailability] = None
    monthly: Optional[MonthlyAvailability] = None


class CategoryServiceResponse(BaseModel):
    id: UUID4
    name: str
    duration: int
    price: float
    discount_price: Optional[float] = None
    status: StatusType
    additional_info: Optional[str] = None
    buffer_before: Optional[int] = 0
    buffer_after: Optional[int] = 0

class CompanyCategoryWithServicesResponse(BaseModel):
    name: str
    description: Optional[str] = None
    services: List['CategoryServiceResponse'] = []

