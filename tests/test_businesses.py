import pytest
from pathlib import Path
import sys

# Add the parent directory to Python path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))


class AuthManager:
    _auth_headers = {}

    @classmethod
    def get_auth_headers(cls, client, professional_data):
        """Get auth headers, registering only once per professional."""
        # Use mobile number as key since it's unique
        mobile = professional_data["mobile_number"]
        if mobile not in cls._auth_headers:
            # Register and login only for the first time
            client.post("/api/v1/professionals/register", json=professional_data)
            login_data = {
                "identifier": mobile,
                "password": professional_data["password"]
            }
            login_response = client.post("/api/v1/professionals/login", json=login_data)
            access_token = login_response.json()["access_token"]
            cls._auth_headers[mobile] = {"Authorization": f"Bearer {access_token}"}
        
        return cls._auth_headers[mobile]


class TestBusinessCreation:
    """Test business creation functionality."""

    def test_create_business_success(self, client, setup_database_module, professional_data):
        """Test successful business creation."""
        # Get auth headers from AuthManager
        headers = AuthManager.get_auth_headers(client, professional_data)

        # Create business
        business_data = {
            "business_name": "Test Salon",
            "description": "A test beauty salon",
            "business_type": "beauty_salon",
            "email": "test@salon.com",
            "phone": "+1234567890",
            "website": "https://testsalon.com",
            "team_size": 5,
            "address": "123 Test St",
            "city": "Test City",
            "state": "Test State",
            "postal_code": "12345",
            "country": "Test Country"
        }
        
        response = client.post("/api/v1/businesses", json=business_data, headers=headers)
        print(response.json())  # Debugging output
        assert response.status_code == 201
        data = response.json()
        
        assert data["business_name"] == business_data["business_name"]
        assert data["business_type"] == business_data["business_type"]
        assert data["email"] == business_data["email"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "owner_id" in data

    def test_create_business_invalid_data(self, client, setup_database_module, professional_data):
        """Test business creation with invalid data."""
        # Get auth headers from AuthManager
        headers = AuthManager.get_auth_headers(client, professional_data)

        # Try to create business with invalid data
        invalid_business_data = {
            "business_name": "",  # Empty name
            "business_type": "invalid_type",  # Invalid business type
            "email": "invalid-email",  # Invalid email
            "status": "invalid"  # Invalid status
        }
        
        response = client.post("/api/v1/businesses", json=invalid_business_data, headers=headers)
        assert response.status_code == 422
        errors = response.json()
        assert "detail" in errors

    def test_create_business_unauthorized(self, client, setup_database_module):
        """Test business creation without authentication."""
        business_data = {
            "business_name": "Test Salon",
            "business_type": "beauty_salon",
        }
        
        response = client.post("/api/v1/businesses/", json=business_data)
        assert response.status_code == 403


class TestBusinessRetrieval:
    """Test business retrieval functionality."""

    def test_get_own_businesses(self, client, setup_database_module, professional_data):
        """Test getting list of own businesses."""
        # Get auth headers from AuthManager
        headers = AuthManager.get_auth_headers(client, professional_data)

        # Create two businesses
        business_data1 = {
            "business_name": "Test Salon 1",
            "business_type": "beauty_salon",
            "email": "test1@salon.com",
            "phone": "+1234567890",
            "status": "active"
        }
        business_data2 = {
            "business_name": "Test Salon 2",
            "business_type": "spa",
            "email": "test2@salon.com",
            "phone": "+1234567890",
            "status": "active"
        }
        
        client.post("/api/v1/businesses", json=business_data1, headers=headers)
        client.post("/api/v1/businesses", json=business_data2, headers=headers)

        # Get list of own businesses
        response = client.get("/api/v1/businesses/my-businesses", headers=headers)
        assert response.status_code == 200
        
        businesses = response.json()
        assert len(businesses) == 3
        assert any(b["business_name"] == business_data1["business_name"] for b in businesses)
        assert any(b["business_name"] == business_data2["business_name"] for b in businesses)

    def test_get_business_by_id(self, client, setup_database_module, professional_data):
        """Test getting a business by ID."""
        # Get auth headers from AuthManager
        headers = AuthManager.get_auth_headers(client, professional_data)

        business_data = {
            "business_name": "Test Salon 5",
            "business_type": "beauty_salon",
            "email": "test123@salon.com",
            "phone": "+1234567890",
        }
        
        create_response = client.post("/api/v1/businesses/", json=business_data, headers=headers)
        business_id = create_response.json()["id"]

        # Get business by ID
        response = client.get(f"/api/v1/businesses/{business_id}", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == business_id
        assert data["business_name"] == business_data["business_name"]

    def test_get_nonexistent_business(self, client, setup_database_module, professional_data):
        """Test getting a non-existent business."""
        # Get auth headers from AuthManager
        headers = AuthManager.get_auth_headers(client, professional_data)

        response = client.get("/api/v1/businesses/99999", headers=headers)
        assert response.status_code == 404
        assert "Business not found" in response.json()["detail"]
