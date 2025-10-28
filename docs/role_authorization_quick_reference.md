# Quick Reference: Role-Based Authorization Implementation

## What Was Implemented

### 1. Core Authorization System (`app/api/dependencies.py`)

Four new dependency functions were added:

- `get_current_user_role()` - Retrieves the user's role from the database
- `require_owner()` - Restricts to owner only
- `require_admin_or_owner()` - Restricts to admin or owner
- `require_staff_or_higher()` - Restricts to staff, admin, or owner
- `require_role(allowed_roles)` - Custom role checker factory

### 2. Protected Endpoints (`app/api/api_v1/endpoints/companies.py`)

The following endpoints now require specific roles:

**Admin or Owner Only:**
- `GET /companies/users` - List all staff
- `PUT /companies` - Update company info
- `POST /companies/emails` - Add company email
- `DELETE /companies/emails/{email_id}` - Remove company email
- `POST /companies/phones` - Add company phone
- `DELETE /companies/phones/{phone_id}` - Remove company phone
- `GET /companies/user-time-offs` - View all user time-offs

**Staff and Above:**
- `GET /companies/customers` - View customer list

## Usage Examples

### Example 1: Protect an Endpoint

```python
from app.api.dependencies import require_admin_or_owner
from app.models.enums import CompanyRoleType

@router.get("/sensitive-data")
async def get_sensitive_data(
    db: Session = Depends(get_db),
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)
):
    """Only admin or owner can access this endpoint"""
    # Your logic here
    pass
```

### Example 2: Custom Role Requirements

```python
from app.api.dependencies import require_role

@router.post("/special-action")
async def special_action(
    user_role: CompanyRoleType = Depends(
        require_role([CompanyRoleType.owner, CompanyRoleType.admin])
    )
):
    """Custom role combination"""
    pass
```

### Example 3: Update User Role

```bash
# Only owner can do this
PUT /roles/users/{user_id}/role
{
  "user_id": "uuid-here",
  "new_role": "admin"
}
```

## Role Hierarchy

```
Owner (Highest)
  ↓
Admin
  ↓
Staff
  ↓
Viewer (Lowest)
```

## API Responses

### Success (200 OK)
```json
{
  "status": "success",
  "message": "Operation completed",
  "data": {...}
}
```

### Forbidden (403)
```json
{
  "status": "error",
  "message": "Insufficient permissions. Required roles: ['owner', 'admin']",
  "data": null
}
```

## Next Steps to Integrate

1. **Register the roles router** in your API:
   ```python
   # In app/api/api_v1/api.py
   from app.api.api_v1.endpoints import roles
   
   api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
   ```

2. **Add more protected endpoints** as needed using the dependency functions

3. **Test with different roles** to ensure proper access control

4. **Update frontend** to handle 403 errors and show appropriate messages

## Testing

```python
# Test that staff cannot access admin endpoints
def test_staff_cannot_list_users(client, staff_token):
    response = client.get(
        "/companies/users",
        cookies={"access_token": staff_token}
    )
    assert response.status_code == 403

# Test that admin can access
def test_admin_can_list_users(client, admin_token):
    response = client.get(
        "/companies/users",
        cookies={"access_token": admin_token}
    )
    assert response.status_code == 200
```

## Security Notes

- Roles are verified on EVERY request via JWT token + database lookup
- Users must belong to the company (checked in `get_current_user_role`)
- Owner cannot remove their own role if they're the last owner
- Role changes require re-authentication for token refresh

