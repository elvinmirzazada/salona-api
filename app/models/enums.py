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

class PhoneStatusType(str, Enum):
    primary = "primary"
    secondary = "secondary"
    unverified = "unverified"

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


class AppointmentStatus(str, Enum):
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