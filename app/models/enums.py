from enum import Enum


class GenderType(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class StatusType(str, Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class EmailStatusType(str, Enum):
    primary = "primary"
    secondary = "secondary"
    unverified = "unverified"

class CustomerEmailStatusType(str, Enum):
    primary = "primary"
    secondary = "secondary"
    unverified = "unverified"

class PhoneStatusType(str, Enum):
    primary = "primary"
    secondary = "secondary"
    unverified = "unverified"

class CompanyRoleType(str, Enum):
    owner = "owner"
    admin = "admin"
    staff = "staff"
    viewer = "viewer"

class CustomerStatusType(str, Enum):
    active = "active"
    pending_verification = "pending_verification"
    disabled = "disabled"

class PriceType(str, Enum):
    FIXED = "fixed"
    FROM = "from"
    FREE = "free"


class SourceType(str, Enum):
    WALK_IN = "walk_in"
    WEBSITE = "website"
    REFERRAL = "referral"
    SOCIAL_MEDIA = "social_media"
    OTHER = "other"


class BookingStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"

class VerificationType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    TWO_FACTOR = "two_factor"

class VerificationStatus(str, Enum):
    PENDING = "pending"
    EXPIRED = "expired"
    VERIFIED = "verified"

class AvailabilityType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class NotificationType(str, Enum):
    BOOKING_CREATED = "booking_created"
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    BOOKING_REMINDER = "booking_reminder"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    GENERAL = "general"


class NotificationStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"


class MembershipPlanType(str, Enum):
    standard = "standard"
    premium = "premium"
    vip = "vip"
