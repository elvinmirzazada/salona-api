# Testing the Professional API

This directory contains comprehensive tests for the Professional API endpoints.

## Test Files

1. **`test_professionals.py`** - Full pytest test suite with database setup
2. **`test_api.py`** - Simple script to test API endpoints manually
3. **`pytest.ini`** - Pytest configuration
4. **`requirements-test.txt`** - Test dependencies

## Running Tests

### Option 1: Full Pytest Suite (Recommended)

1. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

2. Run all tests:
```bash
pytest tests/test_professionals.py -v
```

3. Run specific test class:
```bash
pytest tests/test_professionals.py::TestProfessionalRegistration -v
```

### Option 2: Simple API Test Script

1. Start the API server:
```bash
uvicorn app.main:app --reload
```

2. Run the test script:
```bash
python test_api.py
```

## Test Coverage

The tests cover the following functionality:

### ✅ Professional Registration
- Successful registration
- Duplicate mobile number handling
- Invalid data validation
- Missing field validation

### ✅ Professional Login
- Successful login with mobile number
- Invalid credentials handling
- Wrong password handling
- JWT token generation

### ✅ Authentication & Authorization
- Access token validation
- Refresh token functionality
- Protected endpoint access
- User can only access own data
- Unauthorized access prevention

### ✅ CRUD Operations
- Get current professional info (`/me`)
- Get professional by ID (with authorization)
- Update professional data (with authorization)
- Get professional by mobile number (with authorization)

### ✅ Error Handling
- 401 Unauthorized responses
- 403 Forbidden responses
- 404 Not Found responses
- 422 Validation errors

## Test Data

The tests use the following sample data:

```json
{
  "first_name": "John",
  "last_name": "Doe", 
  "mobile_number": "+1234567890",
  "password": "testpassword123",
  "country": "USA",
  "accept_privacy_policy": true
}
```

## Example API Usage

### 1. Register a Professional
```bash
curl -X POST "http://localhost:8000/api/v1/professionals/register" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "mobile_number": "+1234567890", 
    "password": "securepassword",
    "country": "USA",
    "accept_privacy_policy": true
  }'
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/api/v1/professionals/login" \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "+1234567890",
    "password": "securepassword"
  }'
```

### 3. Access Protected Endpoint
```bash
curl -X GET "http://localhost:8000/api/v1/professionals/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Update Professional
```bash
curl -X PUT "http://localhost:8000/api/v1/professionals/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Johnny",
    "country": "Canada"
  }'
```

### 5. Refresh Token
```bash
curl -X POST "http://localhost:8000/api/v1/professionals/refresh-token" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

## Expected Responses

### Successful Registration (201)
```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "mobile_number": "+1234567890",
  "country": "USA", 
  "accept_privacy_policy": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Successful Login (200)
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 604800
}
```

### Error Response (4xx)
```json
{
  "detail": "Professional with this mobile number already exists"
}
```

## Notes

- All tokens expire after 1 week (604800 seconds)
- Passwords are hashed using bcrypt
- Mobile numbers must be unique
- Users can only access/modify their own data
- All protected endpoints require Bearer token authentication
