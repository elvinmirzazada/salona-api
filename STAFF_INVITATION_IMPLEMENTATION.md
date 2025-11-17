# Staff Member Invitation System - Implementation Summary

## Overview
A complete staff member invitation system has been implemented for inviting staff members to join a company. The system handles both new and existing users with automatic email notifications.

## What Was Implemented

### 1. Database Models & Enums

#### New Enum: `InvitationStatus` (app/models/enums.py)
- `PENDING` - Invitation sent, awaiting response
- `USED` - Invitation accepted
- `EXPIRED` - Invitation expired after 3 days
- `DECLINED` - Invitation declined

#### New Model: `Invitations` (app/models/models.py)
```python
class Invitations(BaseModel):
    __tablename__ = "invitations"
    
    id: UUID (primary key)
    email: String(255) - Email address being invited
    token: String(255) - Unique invitation token
    role: CompanyRoleType - Role to assign (default: staff)
    status: InvitationStatus - Current status
    company_id: UUID - Foreign key to companies
    created_at: DateTime
    updated_at: DateTime
```

**Unique constraint**: `email` + `company_id` to prevent duplicate invitations

### 2. CRUD Operations (app/services/crud/invitation.py)

#### Core Functions:
- **`create_invitation()`** - Creates or updates invitation, generates token
- **`get_invitation_by_token()`** - Retrieves invitation and checks expiration (3 days)
- **`get_invitation_by_email_and_company()`** - Finds invitation by email and company
- **`get_company_invitations()`** - Lists all invitations for a company with optional status filter
- **`accept_invitation()`** - Marks invitation as USED and adds user to company
- **`decline_invitation()`** - Marks invitation as DECLINED
- **`resend_invitation()`** - Regenerates token for expired/pending invitations

### 3. Email Templates (app/services/email_service.py)

#### New Method: `send_staff_invitation_email()`
Sends different email templates based on user status:

**For New Users:**
- Subject: "You're Invited to Join {company_name} on Salona"
- Contains sign-up link
- Encourages account creation

**For Existing Users:**
- Subject: "You've Been Invited to Join a Team!"
- Contains acceptance link
- Different call-to-action

Both templates include:
- Invitation sender name
- Company name
- Acceptance URL with token
- 3-day expiration notice
- Professional HTML formatting

### 4. Pydantic Schemas (app/schemas/schemas.py)

```python
class InvitationBase(BaseModel):
    email: str
    role: Optional[CompanyRoleType] = CompanyRoleType.staff

class InvitationCreate(InvitationBase):
    pass

class InvitationAccept(BaseModel):
    token: str
    first_name: str
    last_name: str
    phone: str
    password: Optional[str] = None  # Required for new users

class Invitation(InvitationBase, TimestampedModel):
    id: UUID4
    company_id: UUID4
    token: Optional[str] = None  # Don't expose in responses
    status: str
```

### 5. API Endpoints (app/api/api_v1/endpoints/companies.py)

#### Endpoint 1: Invite Staff Member
```
POST /companies/{company_id}/invitations
```
**Authentication**: Admin or Owner role required
**Request Body**:
```json
{
  "email": "staff@example.com",
  "role": "staff"  // optional, defaults to staff
}
```
**Response**:
```json
{
  "data": {
    "id": "uuid",
    "email": "staff@example.com",
    "role": "staff",
    "status": "pending",
    "company_id": "uuid",
    "created_at": "2025-11-17T10:00:00",
    "updated_at": "2025-11-17T10:00:00"
  },
  "message": "Staff member invited successfully"
}
```

**Logic**:
- Checks if email exists in system
- Creates invitation with PENDING status
- Sends appropriate email template
- Default role is "staff" if not provided

#### Endpoint 2: Accept Invitation
```
POST /invitations/accept
```
**Authentication**: Not required (public endpoint)
**Request Body**:
```json
{
  "token": "invitation-token-uuid",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "password": "securepass123"  // Required if user doesn't exist
}
```
**Response**:
```json
{
  "message": "Invitation accepted successfully"
}
```

**Logic for New Users**:
- Password is required
- User account is created
- User is added to company with invited role
- Invitation marked as USED
- CompanyUsers record created with status "active"

**Logic for Existing Users**:
- Password is ignored (user already has one)
- User is added to company (or role updated if already member)
- Invitation marked as USED
- CompanyUsers status set to "active"

#### Endpoint 3: Resend Invitation
```
POST /companies/{company_id}/invitations/{token}/resend
```
**Authentication**: Admin or Owner role required
**Response**: Same as invite endpoint

**Logic**:
- Finds invitation by token
- Generates new token
- Resets status to PENDING
- Sends new invitation email

#### Endpoint 4: Get Company Invitations
```
GET /companies/{company_id}/invitations?status_filter=pending
```
**Authentication**: Admin or Owner role required
**Query Parameters**:
- `status_filter` (optional): pending, used, expired, declined

**Response**:
```json
{
  "data": [
    {
      "id": "uuid",
      "email": "staff@example.com",
      "role": "staff",
      "status": "pending",
      "company_id": "uuid",
      "created_at": "2025-11-17T10:00:00",
      "updated_at": "2025-11-17T10:00:00"
    }
  ],
  "message": "Company invitations retrieved successfully"
}
```

## Feature Details

### Invitation Flow

#### Scenario 1: New User
1. Admin/Owner calls: `POST /companies/{id}/invitations` with new email
2. System checks email - not found
3. Creates Invitation record with status=PENDING
4. Sends email with sign-up link and token
5. New user receives email with "Accept Invitation & Sign Up" button
6. User clicks link, goes to frontend with token
7. Frontend shows form with fields: first_name, last_name, phone, password
8. User submits form to `/invitations/accept`
9. System creates new user account
10. System adds user to company with invited role
11. Invitation marked as USED

#### Scenario 2: Existing User
1. Admin/Owner calls: `POST /companies/{id}/invitations` with existing email
2. System checks email - found in database
3. Creates Invitation record with status=PENDING
4. Sends email with acceptance link and token
5. Existing user receives email with "Accept Invitation" button
6. User clicks link, goes to frontend with token
7. Frontend shows form with fields: first_name, last_name, phone (no password)
8. User submits form to `/invitations/accept`
9. System adds user to company (or updates role if already member)
10. Invitation marked as USED
11. CompanyUsers status set to active

#### Scenario 3: Resend Expired Invitation
1. Admin/Owner calls: `POST /companies/{id}/invitations/{token}/resend`
2. System finds invitation
3. Generates new token
4. Resets status to PENDING
5. Resets created_at to current time
6. Sends new invitation email with new token

### Invitation Expiration
- Invitations expire after 3 days
- When `get_invitation_by_token()` is called, it checks if created_at + 3 days < now
- If expired, status is automatically set to EXPIRED and function returns None
- Accept endpoint will fail with 404 for expired invitations

### Role Assignment
- Default role: "staff"
- Can be overridden in invitation creation
- User receives the invited role when accepting
- If user is re-invited to same company, role is updated

### Unique Constraint
- Email + Company combination is unique
- Prevents duplicate pending invitations
- If re-inviting same email to same company, existing invitation is updated with new token

## Database Migration

Run this Alembic migration to create the invitations table:

```python
# In alembic/versions/
def upgrade():
    op.create_table(
        'invitations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('token', sa.String(255), nullable=False, unique=True),
        sa.Column('role', SQLAlchemyEnum(CompanyRoleType), nullable=False, server_default='staff'),
        sa.Column('status', SQLAlchemyEnum(InvitationStatus), nullable=False, server_default='pending'),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', 'company_id', name='_email_company_uc')
    )

def downgrade():
    op.drop_table('invitations')
```

## Security Features

1. **Token-based Invitations**: Uses UUID tokens (cryptographically secure)
2. **Expiration**: 3-day expiration window
3. **Password Hashing**: New user passwords are hashed with bcrypt
4. **Email Verification**: Existing users must click link to verify intent
5. **Role-based Access**: Only admin/owner can invite staff
6. **Unique Constraints**: Prevents invitation spam

## Error Handling

- Invalid token: Returns 404
- Expired invitation: Returns 404
- User already in company: Updates role and status
- Invalid role: Returns 400
- Missing required fields: Returns 400
- Email send failure: Returns 500

## Testing Endpoints

### 1. Invite New User
```bash
curl -X POST http://localhost:8000/api/v1/companies/{company_id}/invitations \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newstaff@example.com",
    "role": "staff"
  }'
```

### 2. Accept Invitation (New User)
```bash
curl -X POST http://localhost:8000/api/v1/invitations/accept \
  -H "Content-Type: application/json" \
  -d '{
    "token": "invitation-token-here",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "password": "securepassword123"
  }'
```

### 3. Accept Invitation (Existing User)
```bash
curl -X POST http://localhost:8000/api/v1/invitations/accept \
  -H "Content-Type: application/json" \
  -d '{
    "token": "invitation-token-here",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890"
  }'
```

### 4. Resend Invitation
```bash
curl -X POST http://localhost:8000/api/v1/companies/{company_id}/invitations/{token}/resend \
  -H "Authorization: Bearer {admin_token}"
```

### 5. List Company Invitations
```bash
curl -X GET http://localhost:8000/api/v1/companies/{company_id}/invitations?status_filter=pending \
  -H "Authorization: Bearer {admin_token}"
```

## Files Modified/Created

**Created:**
- `/app/services/crud/invitation.py` - CRUD operations for invitations

**Modified:**
- `/app/models/enums.py` - Added InvitationStatus enum
- `/app/models/models.py` - Added Invitations model
- `/app/schemas/schemas.py` - Added invitation schemas
- `/app/services/email_service.py` - Added send_staff_invitation_email method
- `/app/api/api_v1/endpoints/companies.py` - Added 4 invitation endpoints

## Next Steps

1. Create and run Alembic migration to add invitations table
2. Configure SendGrid API key in environment variables
3. Set FRONTEND_URL in environment for invitation links
4. Test endpoints with sample data
5. Integrate frontend with token acceptance flow

