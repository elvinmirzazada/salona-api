# Role-Based Authorization Guide

## Overview

This project implements a comprehensive role-based access control (RBAC) system that restricts access to certain endpoints based on user roles within a company.

## Role Hierarchy

The system defines four roles in order of permissions (from highest to lowest):

1. **Owner** - Full control over the company
2. **Admin** - Administrative privileges, can manage most resources
3. **Staff** - Can perform daily operations and access customer data
4. **Viewer** - Read-only access to basic information

These roles are defined in `app/models/enums.py`:

```python
class CompanyRoleType(str, Enum):
    owner = "owner"
    admin = "admin"
    staff = "staff"
    viewer = "viewer"
```

## Authorization Dependencies

The role-based authorization system is implemented through dependency functions in `app/api/dependencies.py`:

### Core Functions

#### `get_current_user_role()`
Retrieves the current user's role in the company from the JWT token and database.

```python
user_role: CompanyRoleType = Depends(get_current_user_role)
```

#### `require_role(allowed_roles: List[CompanyRoleType])`
Factory function to create custom role checkers for specific combinations of roles.

```python
# Allow only owner and admin
role = Depends(require_role([CompanyRoleType.owner, CompanyRoleType.admin]))
```

### Pre-built Role Checkers

#### `require_owner()`
Restricts access to company owners only.

```python
user_role: CompanyRoleType = Depends(require_owner)
```

#### `require_admin_or_owner()`
Allows access to admins and owners.

```python
user_role: CompanyRoleType = Depends(require_admin_or_owner)
```

#### `require_staff_or_higher()`
Allows access to staff, admins, and owners (excludes viewers).

```python
user_role: CompanyRoleType = Depends(require_staff_or_higher)
```

## Usage Examples

### Example 1: Restrict Staff Listing to Admin/Owner

```python
@router.get("/users", response_model=DataResponse[List[CompanyUser]])
async def get_company_users(
    db: Session = Depends(get_db),
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)
) -> DataResponse:
    """
    Get all staff/users in the company.
    Requires admin or owner role.
    """
    users = crud_company.get_company_users(db=db, company_id=company_id)
    return DataResponse.success_response(data=users)
```

### Example 2: Allow Staff to View Customers

```python
@router.get('/customers', response_model=DataResponse[List[Customer]])
async def get_company_customers(
    db: Session = Depends(get_db),
    company_id: str = Depends(get_current_company_id),
    user_role: CompanyRoleType = Depends(require_staff_or_higher)
) -> DataResponse:
    """
    Get all customers.
    Requires staff, admin, or owner role.
    """
    customers = crud_customer.get_company_customers(db=db, company_id=company_id)
    return DataResponse.success_response(data=customers)
```

### Example 3: Owner-Only Operations

```python
@router.delete("/company/{company_id}", response_model=DataResponse)
async def delete_company(
    company_id: str,
    db: Session = Depends(get_db),
    user_role: CompanyRoleType = Depends(require_owner)
) -> DataResponse:
    """
    Delete a company.
    Only the owner can delete the company.
    """
    # ... deletion logic
```

### Example 4: Custom Role Combinations

```python
from app.api.dependencies import require_role
from app.models.enums import CompanyRoleType

@router.post("/special-action")
async def special_action(
    user_role: CompanyRoleType = Depends(
        require_role([CompanyRoleType.owner, CompanyRoleType.admin])
    )
):
    """
    Perform special action.
    Only owners and admins can perform this action.
    """
    # ... action logic
```

## Protected Endpoints

The following endpoints now have role-based authorization:

### Admin/Owner Only
- `GET /companies/users` - List all staff members
- `PUT /companies` - Update company information
- `POST /companies/emails` - Add company emails
- `DELETE /companies/emails/{email_id}` - Delete company emails
- `POST /companies/phones` - Add company phones
- `DELETE /companies/phones/{phone_id}` - Delete company phones
- `GET /companies/user-time-offs` - View all user time-offs

### Staff and Above
- `GET /companies/customers` - View customer list

## Error Responses

When a user attempts to access a resource without proper permissions, they receive:

```json
{
  "status": "error",
  "message": "Insufficient permissions. Required roles: ['owner', 'admin']",
  "data": null
}
```

HTTP Status Code: `403 Forbidden`

## How Roles are Assigned

Roles are stored in the `company_users` table which links users to companies with their respective roles:

```sql
CREATE TABLE company_users (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    company_id UUID REFERENCES companies(id),
    role VARCHAR,  -- owner, admin, staff, viewer
    status VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

When a user logs in, their role is retrieved from this table and can be checked for each request.

## Best Practices

1. **Always specify role requirements** for sensitive endpoints
2. **Use the most restrictive role** that makes sense for the operation
3. **Document role requirements** in endpoint docstrings
4. **Test with different roles** to ensure proper access control
5. **Combine with company_id checks** to ensure users can only access their company's data

## Adding New Role-Protected Endpoints

1. Import the required dependencies:
```python
from app.api.dependencies import require_admin_or_owner, require_staff_or_higher
from app.models.enums import CompanyRoleType
```

2. Add the role dependency to your endpoint:
```python
@router.post("/sensitive-operation")
async def sensitive_operation(
    db: Session = Depends(get_db),
    user_role: CompanyRoleType = Depends(require_admin_or_owner)
):
    # Your logic here
    pass
```

3. Document the required role in the docstring:
```python
"""
Perform a sensitive operation.
Requires admin or owner role.
"""
```

## Testing Role-Based Authorization

To test role-based authorization:

1. Create test users with different roles
2. Authenticate as each user type
3. Attempt to access protected endpoints
4. Verify that proper 403 errors are returned for unauthorized access

Example test structure:
```python
def test_staff_list_requires_admin(client, regular_staff_token):
    """Test that regular staff cannot list all users"""
    response = client.get(
        "/companies/users",
        cookies={"access_token": regular_staff_token}
    )
    assert response.status_code == 403
    
def test_admin_can_list_staff(client, admin_token):
    """Test that admin can list all users"""
    response = client.get(
        "/companies/users",
        cookies={"access_token": admin_token}
    )
    assert response.status_code == 200
```

## Security Considerations

- **JWT tokens contain company_id**: Ensure tokens are properly signed and validated
- **Database validation**: Always verify the user belongs to the company in the database
- **Role changes**: When a user's role changes, they should re-authenticate to get a fresh token
- **Least privilege**: Default to the most restrictive role and explicitly grant higher permissions

## Future Enhancements

Consider implementing:
- **Resource-based permissions**: Fine-grained control over specific resources
- **Permission inheritance**: More complex role hierarchies
- **Temporary role elevation**: Time-limited elevated permissions
- **Audit logging**: Track all role-based access attempts
- **Role management endpoints**: Allow owners to change user roles

