# UTC Timezone Implementation

## Overview
All datetime operations in the Salona API have been standardized to use UTC timezone for consistency and to avoid timezone-related bugs.

## Changes Made

### 1. Core Utilities (`app/core/datetime_utils.py`)
Created a centralized utility module with helper functions:
- `utcnow()` - Get current UTC datetime (timezone-aware)
- `ensure_utc()` - Ensure a datetime is timezone-aware in UTC
- `make_naive_utc()` - Convert timezone-aware datetime to naive UTC

### 2. Database Configuration (`app/db/session.py`)
- Added PostgreSQL connection-level timezone configuration
- Implemented event listener to set timezone to UTC for each database connection
- This ensures all database operations use UTC timezone

### 3. CRUD Services
Updated all CRUD services to use `datetime.now(timezone.utc)` instead of `datetime.now()`:

#### `app/services/crud/customer.py`
- `verify_token()` - Uses UTC for `used_at` timestamp

#### `app/services/crud/user.py`
- `verify_token()` - Uses UTC for `used_at` timestamp

#### `app/services/crud/membership.py`
- `create()` - Uses UTC for `start_date` and `end_date` calculation
- `get_active_membership()` - Uses UTC for membership expiration check

#### `app/services/crud/invitation.py`
- `create_invitation()` - Uses UTC for `updated_at` timestamp
- `get_invitation_by_token()` - Uses UTC for expiration check
- `accept_invitation()` - Uses UTC for `updated_at` timestamp
- `decline_invitation()` - Uses UTC for `updated_at` timestamp
- `resend_invitation()` - Uses UTC for `created_at` and `updated_at` timestamps

### 4. Email Service (`app/services/email_service.py`)
- `create_verification_token()` - Uses UTC for token expiration calculation

### 5. Schemas (`app/schemas/schemas.py`)
- `NotificationBase.created_at` - Default factory now uses `datetime.now(timezone.utc)`

### 6. Auth Service (`app/services/auth.py`)
Already using UTC correctly with `datetime.now(dt_obj.UTC)` for JWT token expiration.

### 7. Booking Service (`app/services/crud/booking.py`)
Already has `ensure_timezone_aware()` helper function for UTC handling.

## Database Models
The models use `func.now()` which respects the database timezone setting. With our PostgreSQL configuration set to UTC, all timestamps will be stored in UTC.

## Best Practices

### When Creating New Code
1. **Always use timezone-aware datetimes:**
   ```python
   from datetime import datetime, timezone
   current_time = datetime.now(timezone.utc)
   ```

2. **Or use the utility function:**
   ```python
   from app.core.datetime_utils import utcnow
   current_time = utcnow()
   ```

3. **When comparing datetimes:**
   ```python
   from datetime import datetime, timezone
   if some_datetime > datetime.now(timezone.utc):
       # Future datetime
   ```

4. **For database queries with datetime filters:**
   ```python
   from app.core.datetime_utils import utcnow
   active_items = db.query(Model).filter(Model.expires_at > utcnow()).all()
   ```

### API Request/Response
- FastAPI automatically handles timezone serialization in JSON responses
- Client applications should convert UTC times to local timezone for display
- All datetime inputs from clients should be sent in ISO 8601 format with timezone info

## Testing
All datetime comparisons and operations now use UTC consistently:
- Token expiration checks
- Membership expiration checks
- Invitation expiration checks
- Booking time validations

## Migration Notes
- Existing data in the database remains unchanged
- New datetime values will be stored in UTC
- The database timezone setting ensures consistency at the storage level

## Benefits
1. **Consistency** - All datetimes across the application use the same timezone
2. **No ambiguity** - UTC has no daylight saving time changes
3. **Global compatibility** - Easy to convert to any local timezone in client applications
4. **Debugging** - Easier to trace and debug datetime-related issues

