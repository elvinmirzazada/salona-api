# Example: Integrating Membership into Existing Endpoints

This file demonstrates how to add membership functionality to your existing API endpoints.

## Example 1: Add Booking Limit Check to Booking Endpoint

### Before (Original bookings.py):
```python
@router.post("", response_model=DataResponse[Booking])
async def create_booking(
    *,
    db: Session = Depends(get_db),
    booking_in: BookingCreate,
    response: Response
) -> DataResponse:
    # Create booking logic
    pass
```

### After (With Membership Integration):
```python
from app.api.membership_dependencies import check_booking_limit
from app.services.crud import membership as crud_membership

@router.post("", response_model=DataResponse[Booking])
async def create_booking(
    *,
    db: Session = Depends(get_db),
    booking_in: BookingCreate,
    response: Response,
    can_book: bool = Depends(check_booking_limit)  # Add this dependency
) -> DataResponse:
    """
    Create a new booking.
    Checks membership booking limits if customer is authenticated.
    """
    # Existing booking creation logic...
    
    # After successful booking, increment booking count if customer has membership
    if customer_id:
        crud_membership.customer_membership.increment_booking_count(
            db, customer_id=str(customer_id)
        )
    
    return DataResponse.success_response(data=booking, message="Booking created")
```

## Example 2: Premium-Only Endpoint

### Add a new premium booking endpoint:
```python
from app.api.membership_dependencies import require_customer_membership
from app.models.enums import MembershipPlanType

@router.post("/priority-booking", response_model=DataResponse[Booking])
async def create_priority_booking(
    *,
    db: Session = Depends(get_db),
    booking_in: BookingCreate,
    plan: MembershipPlanType = Depends(
        require_customer_membership(min_plan=MembershipPlanType.PREMIUM)
    )
) -> DataResponse:
    """
    Create a priority booking (Premium and VIP members only).
    Premium members get priority time slots.
    """
    # Only Premium and VIP members can access this endpoint
    # Create priority booking logic here
    pass
```

## Example 3: Apply Membership Discounts

### Update booking price calculation:
```python
from app.services.crud import membership as crud_membership

def calculate_booking_price(db: Session, customer_id: str, services: List[ServiceItem]) -> int:
    """Calculate total booking price with membership discount if applicable."""
    base_price = sum(service.price for service in services)
    
    # Check for active membership
    membership = crud_membership.customer_membership.get_active_membership(
        db, customer_id=customer_id
    )
    
    if membership and membership.membership_plan:
        discount_percentage = membership.membership_plan.discount_percentage
        discount_amount = (base_price * discount_percentage) // 100
        final_price = base_price - discount_amount
        return final_price
    
    return base_price
```

## Example 4: VIP-Only Feature

### Add VIP exclusive services endpoint:
```python
@router.get("/vip-services", response_model=DataResponse[List[Service]])
async def get_vip_services(
    *,
    db: Session = Depends(get_db),
    plan: MembershipPlanType = Depends(
        require_customer_membership(allowed_plans=[MembershipPlanType.VIP])
    )
) -> DataResponse:
    """
    Get VIP-exclusive services (VIP members only).
    """
    # Return exclusive services for VIP members
    services = get_exclusive_vip_services(db)
    return DataResponse.success_response(data=services)
```

## Example 5: Company Feature with Membership

### Add advanced analytics for Premium+ companies:
```python
from app.api.membership_dependencies import require_company_membership

@router.get("/analytics/advanced", response_model=DataResponse[AnalyticsData])
async def get_advanced_analytics(
    *,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_current_company_id),
    plan: MembershipPlanType = Depends(
        require_company_membership(min_plan=MembershipPlanType.PREMIUM)
    )
) -> DataResponse:
    """
    Get advanced analytics (Premium and VIP companies only).
    """
    analytics = calculate_advanced_analytics(db, company_id)
    return DataResponse.success_response(data=analytics)
```

## Example 6: Optional Membership Benefits

### Show different data based on membership level:
```python
from app.api.membership_dependencies import get_customer_membership_plan

@router.get("/services", response_model=DataResponse[List[Service]])
async def list_services(
    *,
    db: Session = Depends(get_db),
    customer_plan: Optional[MembershipPlanType] = Depends(get_customer_membership_plan)
) -> DataResponse:
    """
    List services with pricing based on membership level.
    """
    services = get_all_services(db)
    
    # Apply discount if customer has membership
    if customer_plan:
        membership = crud_membership.customer_membership.get_active_membership(
            db, customer_id=current_customer.id
        )
        if membership:
            discount = membership.membership_plan.discount_percentage
            for service in services:
                service.discounted_price = service.price * (100 - discount) // 100
    
    return DataResponse.success_response(data=services)
```

## Example 7: Booking Cancellation with Membership Rules

### Different cancellation policies based on membership:
```python
from datetime import datetime, timedelta

@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(
    *,
    db: Session = Depends(get_db),
    booking_id: str,
    current_customer: Customers = Depends(get_current_active_customer)
) -> DataResponse:
    """
    Cancel a booking. Cancellation policy depends on membership level.
    """
    booking = get_booking(db, booking_id)
    
    # Check membership for cancellation window
    membership = crud_membership.customer_membership.get_active_membership(
        db, customer_id=str(current_customer.id)
    )
    
    if membership and membership.membership_plan:
        cancellation_hours = membership.membership_plan.cancellation_hours
    else:
        cancellation_hours = 24  # Default for non-members
    
    # Check if within cancellation window
    time_until_booking = booking.start_at - datetime.now()
    if time_until_booking < timedelta(hours=cancellation_hours):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bookings must be cancelled at least {cancellation_hours} hours in advance"
        )
    
    # Cancel the booking
    cancel_booking_logic(db, booking_id)
    return DataResponse.success_response(message="Booking cancelled successfully")
```

## Example 8: Membership Status in User Profile

### Include membership info in customer profile endpoint:
```python
@router.get("/profile", response_model=DataResponse[CustomerProfile])
async def get_customer_profile(
    *,
    db: Session = Depends(get_db),
    current_customer: Customers = Depends(get_current_active_customer)
) -> DataResponse:
    """
    Get customer profile including membership information.
    """
    profile = get_basic_profile(current_customer)
    
    # Add membership info
    membership = crud_membership.customer_membership.get_active_membership(
        db, customer_id=str(current_customer.id)
    )
    
    if membership and membership.membership_plan:
        profile.membership = {
            "plan": membership.membership_plan.plan_type.value,
            "status": membership.status.value,
            "expires_at": membership.end_date,
            "bookings_remaining": (
                membership.membership_plan.max_bookings_per_month - membership.bookings_used
                if membership.membership_plan.max_bookings_per_month
                else None
            ),
            "discount_percentage": membership.membership_plan.discount_percentage
        }
    else:
        profile.membership = None
    
    return DataResponse.success_response(data=profile)
```

## Migration Instructions

1. **Run the database migration:**
   ```bash
   alembic upgrade head
   ```

2. **Update existing endpoints gradually:**
   - Start with booking endpoints (add limit checks)
   - Add premium features as new endpoints
   - Update pricing logic to include discounts
   - Implement membership-specific cancellation policies

3. **Test each integration:**
   - Test without membership (existing behavior)
   - Test with Standard membership
   - Test with Premium membership
   - Test with VIP membership
   - Test expired memberships
   - Test booking limits

4. **Common patterns to use:**
   - `Depends(check_booking_limit)` - Check booking limits
   - `Depends(require_customer_membership(min_plan=X))` - Require minimum membership
   - `Depends(require_company_membership(min_plan=X))` - Require company membership
   - `Depends(get_customer_membership_plan)` - Get optional membership info

