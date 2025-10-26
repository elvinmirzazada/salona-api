from datetime import datetime, date, time
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, UUID4

from app.models import CustomerStatusType, CompanyCategories
from app.models.enums import GenderType, StatusType, PriceType, SourceType, BookingStatus, AvailabilityType, EmailStatusType, PhoneStatusType, NotificationType, NotificationStatus


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
    company_id: Optional[UUID4] = None
    status: CustomerStatusType


class CompanyUser(TimestampedModel):
    id: UUID4
    user_id: UUID4
    company_id: UUID4
    role: str
    status: StatusType

    user: Optional[User] = None
    model_config = ConfigDict(from_attributes=True)


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


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    team_size: Optional[int] = None
    status: Optional[StatusType] = None


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
    
    id: UUID4
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
    id: Optional[UUID4] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class BookingServiceRequest(BaseModel):
    category_service_id: UUID4
    user_id: UUID4
    notes: Optional[str] = None

class BookingCreate(BaseModel):
    company_id: Optional[UUID4] = None
    start_time: datetime
    services: List[BookingServiceRequest]
    notes: Optional[str] = None
    customer_info: Optional[GuestCustomerInfo] = None  # For unregistered customers


class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[BookingStatus] = None
    services: Optional[List[BookingServiceRequest]] = None




class BookingService(TimestampedModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    booking_id: UUID4
    category_service_id: UUID4
    user_id: UUID4
    notes: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # service: Optional[CompanyCategories] = None
    # assigned_user: Optional[CompanyUser] = None


class Booking(BookingBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    total_price: int
    customer: Optional[Customer] = None
    booking_services: Optional[List[BookingService]] = []
    user_ids: set[str] = set([])


#
class CompanyCustomers(Company):

    model_config = ConfigDict(from_attributes=True)
    customers: List[Customer] = []

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
    user_id: Optional[str]
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

class CategoryServiceBase(BaseModel):
    name: str
    duration: int
    price: float
    discount_price: Optional[float] = None
    additional_info: Optional[str] = None
    status: StatusType = StatusType.active
    buffer_before: Optional[int] = 0
    buffer_after: Optional[int] = 0

class CategoryServiceCreate(CategoryServiceBase):
    category_id: str

class CategoryServiceUpdate(BaseModel):
    name: Optional[str] = None
    duration: Optional[int] = None
    price: Optional[float] = None
    discount_price: Optional[float] = None
    additional_info: Optional[str] = None
    status: Optional[StatusType] = None
    buffer_before: Optional[int] = None
    buffer_after: Optional[int] = None


class CompanyCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CompanyCategoryCreate(CompanyCategoryBase):
    company_id: Optional[str] = None

class CompanyCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    company_id: Optional[str] = None

class CompanyCategory(CompanyCategoryBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    company_id: UUID4


# CompanyCategoryWithServicesResponse already exists
class CompanyCategoryWithServicesResponse(BaseModel):
    id: UUID4
    name: str
    description: Optional[str] = None
    services: List['CategoryServiceResponse'] = []

# Time Off schemas
class TimeOffBase(BaseModel):
    start_date: datetime
    end_date: datetime
    user_id: UUID4
    reason: Optional[str] = None

class TimeOffCreate(TimeOffBase):
    pass

class TimeOffUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None

class TimeOff(TimeOffBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    user: User


class CompanyEmailBase(BaseModel):
    email: EmailStr
    status: EmailStatusType = EmailStatusType.unverified

class CompanyEmailCreate(BaseModel):
    emails: List[CompanyEmailBase] = []
    company_id: Optional[str] = None

class CompanyEmail(CompanyEmailBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    company_id: UUID4


class CompanyPhoneBase(BaseModel):
    phone: str
    is_primary: bool = False
    status: PhoneStatusType = PhoneStatusType.unverified

class CompanyPhoneCreate(BaseModel):
    company_phones: List[CompanyPhoneBase] = []
    company_id: Optional[str] = None

class CompanyPhone(CompanyPhoneBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    company_id: UUID4


class NotificationBase(BaseModel):
    type: NotificationType
    message: str
    data: Optional[str] = None
    status: NotificationStatus = NotificationStatus.UNREAD
    created_at: datetime = datetime.now()


class NotificationCreate(NotificationBase):
    pass


class CompanyNotificationCreate(NotificationCreate):
    company_id: Optional[UUID4] = None


class NotificationUpdate(BaseModel):
    status: Optional[NotificationStatus] = None

class Notification(NotificationBase, TimestampedModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    company_id: UUID4

