# Membership System Documentation

## Overview

The membership system provides three tiers of membership plans for both customers and companies:
- **Standard**: Basic membership with limited benefits
- **Premium**: Enhanced membership with better benefits  
- **VIP**: Top-tier membership with unlimited access and premium benefits

## Membership Plans

### Default Plans Configuration

| Plan | Price | Bookings/Month | Discount | Priority Booking | Cancellation Window |
|------|-------|----------------|----------|------------------|---------------------|
| Standard | $9.99 | 5 | 5% | No | 24 hours |
| Premium | $19.99 | 15 | 10% | Yes | 48 hours |
| VIP | $49.99 | Unlimited | 20% | Yes | 72 hours |

### Features by Plan

**Standard:**
- Email support
- 7-day booking window
- 5% discount on services
- 5 bookings per month

**Premium:**
- Priority email support
- 14-day booking window
- 10% discount on services
- 15 bookings per month
- Access to exclusive services
- Priority booking slots

**VIP:**
- 24/7 phone support
- 30-day booking window
- 20% discount on services
- Unlimited bookings
- Access to exclusive services
- Priority booking slots
- Concierge service

## API Endpoints

### Membership Plans Management

#### List All Plans
```http
GET /api/v1/memberships/plans
```

Query Parameters:
- `skip` (int): Number of records to skip (default: 0)
- `limit` (int): Maximum number of records (default: 100)
- `active_only` (bool): Show only active plans (default: true)

#### Get Plan by Type
```http
GET /api/v1/memberships/plans/type/{plan_type}
```

Path Parameters:
- `plan_type`: standard | premium | vip

#### Create Plan (Admin)
```http
POST /api/v1/memberships/plans
```

Request Body:
```json
{
  "name": "Premium Plus",
  "plan_type": "premium",
  "description": "Enhanced premium membership",
  "price": 2999,
  "duration_days": 30,
  "max_bookings_per_month": 20,
  "discount_percentage": 15,
  "priority_booking": true,
  "cancellation_hours": 48,
  "features": "{\"support\": \"priority\", \"extras\": [\"feature1\"]}"
}
```

#### Update Plan (Admin)
```http
PATCH /api/v1/memberships/plans/{plan_id}
```

#### Delete Plan (Admin)
```http
DELETE /api/v1/memberships/plans/{plan_id}
```

### Customer Memberships

#### Subscribe to Plan
```http
POST /api/v1/memberships/customer/subscribe
```

Request Body:
```json
{
  "membership_plan_id": "uuid-here",
  "auto_renew": true
}
```

Authentication: Customer JWT required

#### Get Membership Status
```http
GET /api/v1/memberships/customer/status
```

Returns:
```json
{
  "success": true,
  "data": {
    "has_membership": true,
    "plan_type": "premium",
    "plan_name": "Premium Membership",
    "status": "active",
    "end_date": "2025-11-30T12:00:00",
    "bookings_remaining": 12,
    "discount_percentage": 10,
    "priority_booking": true
  }
}
```

#### Get All Customer Memberships
```http
GET /api/v1/memberships/customer/memberships
```

Shows current and past memberships.

#### Update Membership
```http
PATCH /api/v1/memberships/customer/memberships/{membership_id}
```

Request Body:
```json
{
  "auto_renew": false
}
```

#### Cancel Membership
```http
POST /api/v1/memberships/customer/memberships/{membership_id}/cancel
```

### Company Memberships

#### Subscribe Company to Plan (Admin/Owner)
```http
POST /api/v1/memberships/company/subscribe
```

Request Body:
```json
{
  "membership_plan_id": "uuid-here",
  "auto_renew": true
}
```

#### Get Company Membership Status
```http
GET /api/v1/memberships/company/status
```

#### Get All Company Memberships
```http
GET /api/v1/memberships/company/memberships
```

#### Cancel Company Membership (Admin/Owner)
```http
POST /api/v1/memberships/company/memberships/{membership_id}/cancel
```

## Using Membership Dependencies

### Require Specific Membership

You can protect endpoints to require specific membership tiers:

```python
from fastapi import APIRouter, Depends
from app.api.membership_dependencies import require_customer_membership
from app.models.enums import MembershipPlanType

router = APIRouter()

# Require at least Premium membership
@router.post("/premium-only-feature")
async def premium_feature(
    plan: MembershipPlanType = Depends(
        require_customer_membership(min_plan=MembershipPlanType.PREMIUM)
    )
):
    # Only Premium and VIP members can access
    return {"message": "Premium feature accessed"}

# Require VIP membership only
@router.post("/vip-exclusive")
async def vip_feature(
    plan: MembershipPlanType = Depends(
        require_customer_membership(
            allowed_plans=[MembershipPlanType.VIP]
        )
    )
):
    # Only VIP members can access
    return {"message": "VIP exclusive feature"}
```

### Check Booking Limits

Add booking limit checks to booking endpoints:

```python
from app.api.membership_dependencies import check_booking_limit

@router.post("/bookings")
async def create_booking(
    booking_data: BookingCreate,
    can_book: bool = Depends(check_booking_limit)
):
    # Will raise 403 if customer has exceeded their monthly limit
    # Create booking logic here
    pass
```

### Company Membership Requirements

```python
from app.api.membership_dependencies import require_company_membership

@router.post("/advanced-analytics")
async def get_advanced_analytics(
    plan: MembershipPlanType = Depends(
        require_company_membership(min_plan=MembershipPlanType.PREMIUM)
    )
):
    # Only Premium and VIP companies can access
    return {"analytics": "data"}
```

## Example Usage Scenarios

### Scenario 1: Customer Subscribes to Premium

1. Customer lists available plans:
   ```http
   GET /api/v1/memberships/plans
   ```

2. Customer subscribes to Premium:
   ```http
   POST /api/v1/memberships/customer/subscribe
   {
     "membership_plan_id": "premium-plan-uuid",
     "auto_renew": true
   }
   ```

3. Customer checks their status:
   ```http
   GET /api/v1/memberships/customer/status
   ```

### Scenario 2: Protecting an Endpoint

In your booking endpoint, add membership checks:

```python
# Before modification
@router.post("/bookings/priority")
async def create_priority_booking(booking: BookingCreate):
    # Any customer can access
    pass

# After modification - Premium+ only
@router.post("/bookings/priority")
async def create_priority_booking(
    booking: BookingCreate,
    plan: MembershipPlanType = Depends(
        require_customer_membership(min_plan=MembershipPlanType.PREMIUM)
    )
):
    # Only Premium and VIP members can access priority booking
    pass
```

### Scenario 3: Apply Membership Discounts

In your booking service, check for membership discounts:

```python
from app.services.crud import membership as crud_membership

def calculate_booking_price(db: Session, customer_id: str, base_price: int):
    # Get active membership
    membership = crud_membership.customer_membership.get_active_membership(
        db, customer_id=customer_id
    )
    
    if membership and membership.membership_plan:
        discount = membership.membership_plan.discount_percentage
        discounted_price = base_price * (100 - discount) // 100
        return discounted_price
    
    return base_price
```

## Database Schema

### Tables Created

1. **membership_plans**: Stores membership plan definitions
2. **customer_memberships**: Links customers to their subscriptions
3. **company_memberships**: Links companies to their subscriptions

### Key Relationships

- CustomerMemberships → Customers (many-to-one)
- CustomerMemberships → MembershipPlans (many-to-one)
- CompanyMemberships → Companies (many-to-one)
- CompanyMemberships → MembershipPlans (many-to-one)

### Constraints

- Only one active membership per customer at a time
- Only one active membership per company at a time
- Unique plan types (only one Standard, Premium, VIP plan)

## Migration

Run the database migration:

```bash
# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

This will:
- Create the membership tables
- Add the MembershipPlanType enum
- Insert default Standard, Premium, and VIP plans

## Best Practices

1. **Always check membership limits**: Use `check_booking_limit` dependency for booking endpoints
2. **Apply discounts automatically**: Check for active membership when calculating prices
3. **Use minimum plan level**: Use `min_plan` parameter for hierarchical access (Standard < Premium < VIP)
4. **Track feature usage**: Increment booking counts using `increment_booking_count`
5. **Handle expired memberships**: Memberships automatically expire based on `end_date`
6. **Support auto-renewal**: Handle auto-renewal logic in your payment processing

## Error Handling

The system returns these HTTP errors:

- `401 Unauthorized`: Customer not authenticated
- `403 Forbidden`: 
  - No active membership when required
  - Insufficient membership level
  - Booking limit exceeded
- `404 Not Found`: Membership plan or subscription not found
- `400 Bad Request`: Invalid request data

## Testing

Test different membership scenarios:

```python
# Test without membership
# Test with Standard membership
# Test with Premium membership  
# Test with VIP membership
# Test booking limits
# Test expired memberships
# Test membership upgrades/downgrades
```

