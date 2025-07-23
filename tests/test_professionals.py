import pytest
import sys
import os
from pathlib import Path

# Add the parent directory to Python path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestProfessionalRegistration:
    """Test professional registration functionality."""

    def test_register_professional_success(self, client, setup_database, professional_data):
        """Test successful professional registration."""
        response = client.post("/api/v1/professionals/register", json=professional_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == professional_data["first_name"]
        assert data["last_name"] == professional_data["last_name"]
        assert data["mobile_number"] == professional_data["mobile_number"]
        assert data["country"] == professional_data["country"]
        assert data["accept_privacy_policy"] == professional_data["accept_privacy_policy"]
        assert "password" not in data  # Password should not be returned
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_register_professional_duplicate_mobile(self, client, setup_database, professional_data):
        """Test registration with duplicate mobile number."""
        # First registration should succeed
        response1 = client.post("/api/v1/professionals/register", json=professional_data)
        assert response1.status_code == 201

        # Second registration with same mobile should fail
        response2 = client.post("/api/v1/professionals/register", json=professional_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]

    def test_register_professional_invalid_data(self, client, setup_database):
        """Test registration with invalid data."""
        invalid_data = {
            "first_name": "",  # Empty name
            "mobile_number": "+1234567890",
            "password": "test",
            "country": "USA",
            "accept_privacy_policy": True
        }
        
        response = client.post("/api/v1/professionals/register", json=invalid_data)
        assert response.status_code == 422  # Validation error

    def test_register_professional_missing_fields(self, client, setup_database):
        """Test registration with missing required fields."""
        incomplete_data = {
            "first_name": "John",
            # Missing required fields
        }
        
        response = client.post("/api/v1/professionals/register", json=incomplete_data)
        assert response.status_code == 422


class TestProfessionalLogin:
    """Test professional login functionality."""

    def test_login_success(self, client, setup_database, professional_data):
        """Test successful login."""
        # First register a professional
        register_response = client.post("/api/v1/professionals/register", json=professional_data)
        assert register_response.status_code == 201
        
        # Then try to login
        login_data = {
            "identifier": professional_data["mobile_number"],
            "password": professional_data["password"]
        }
        
        response = client.post("/api/v1/professionals/login", json=login_data)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_invalid_mobile(self, client, setup_database):
        """Test login with non-existent mobile number."""
        login_data = {
            "identifier": "+9999999999",
            "password": "somepassword"
        }
        
        response = client.post("/api/v1/professionals/login", json=login_data)
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_wrong_password(self, client, setup_database, professional_data):
        """Test login with wrong password."""
        # Register professional
        register_response = client.post("/api/v1/professionals/register", json=professional_data)
        assert register_response.status_code == 201
        
        # Try login with wrong password
        login_data = {
            "identifier": professional_data["mobile_number"],
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/professionals/login", json=login_data)
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]


class TestProfessionalAuthentication:
    """Test authentication-required endpoints."""

    def get_auth_headers(self, client, professional_data):
        """Helper method to get authentication headers."""
        # Register professional
        register_response = client.post("/api/v1/professionals/register", json=professional_data)
        professional_id = register_response.json()["id"]
        
        # Login to get tokens
        login_data = {
            "identifier": professional_data["mobile_number"],
            "password": professional_data["password"]
        }
        login_response = client.post("/api/v1/professionals/login", json=login_data)
        access_token = login_response.json()["access_token"]
        
        return {
            "Authorization": f"Bearer {access_token}",
            "professional_id": professional_id
        }

    def test_get_current_professional_info(self, client, setup_database, professional_data):
        """Test getting current professional info with valid token."""
        auth_data = self.get_auth_headers(client, professional_data)
        headers = {"Authorization": auth_data["Authorization"]}
        
        response = client.get("/api/v1/professionals/me", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["mobile_number"] == professional_data["mobile_number"]
        assert data["first_name"] == professional_data["first_name"]

    def test_get_professional_by_id_own_data(self, client, setup_database, professional_data):
        """Test getting professional by ID (own data)."""
        auth_data = self.get_auth_headers(client, professional_data)
        headers = {"Authorization": auth_data["Authorization"]}
        professional_id = auth_data["professional_id"]
        
        response = client.get(f"/api/v1/professionals/{professional_id}", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == professional_id
        assert data["mobile_number"] == professional_data["mobile_number"]

    def test_get_professional_by_id_other_data(self, client, setup_database, professional_data, another_professional_data):
        """Test getting professional by ID (other's data) - should fail."""
        # Register first professional and get auth
        auth_data = self.get_auth_headers(client, professional_data)
        headers = {"Authorization": auth_data["Authorization"]}
        
        # Register second professional
        register_response = client.post("/api/v1/professionals/register", json=another_professional_data)
        other_professional_id = register_response.json()["id"]
        
        # Try to access other professional's data
        response = client.get(f"/api/v1/professionals/{other_professional_id}", headers=headers)
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]

    def test_update_professional_own_data(self, client, setup_database, professional_data):
        """Test updating own professional data."""
        auth_data = self.get_auth_headers(client, professional_data)
        headers = {"Authorization": auth_data["Authorization"]}
        professional_id = auth_data["professional_id"]
        
        update_data = {
            "first_name": "UpdatedName",
            "country": "UpdatedCountry"
        }
        
        response = client.put(f"/api/v1/professionals/{professional_id}", json=update_data, headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["first_name"] == "UpdatedName"
        assert data["country"] == "UpdatedCountry"
        assert data["mobile_number"] == professional_data["mobile_number"]  # Should not change

    def test_update_professional_other_data(self, client, setup_database, professional_data, another_professional_data):
        """Test updating other professional's data - should fail."""
        # Register first professional and get auth
        auth_data = self.get_auth_headers(client, professional_data)
        headers = {"Authorization": auth_data["Authorization"]}
        
        # Register second professional
        register_response = client.post("/api/v1/professionals/register", json=another_professional_data)
        other_professional_id = register_response.json()["id"]
        
        update_data = {"first_name": "Hacker"}
        
        # Try to update other professional's data
        response = client.put(f"/api/v1/professionals/{other_professional_id}", json=update_data, headers=headers)
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]

    def test_get_professional_by_mobile_own_data(self, client, setup_database, professional_data):
        """Test getting professional by mobile number (own data)."""
        auth_data = self.get_auth_headers(client, professional_data)
        headers = {"Authorization": auth_data["Authorization"]}
        
        response = client.get(f"/api/v1/professionals/mobile/{professional_data['mobile_number']}", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["mobile_number"] == professional_data["mobile_number"]

    def test_get_professional_by_mobile_other_data(self, client, setup_database, professional_data, another_professional_data):
        """Test getting professional by mobile number (other's data) - should fail."""
        # Register first professional and get auth
        auth_data = self.get_auth_headers(client, professional_data)
        headers = {"Authorization": auth_data["Authorization"]}
        
        # Register second professional
        client.post("/api/v1/professionals/register", json=another_professional_data)
        
        # Try to access other professional's data by mobile
        response = client.get(f"/api/v1/professionals/mobile/{another_professional_data['mobile_number']}", headers=headers)
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]

    def test_unauthorized_access(self, client, setup_database, professional_data):
        """Test accessing protected endpoints without authentication."""
        # Register professional to get a valid ID
        register_response = client.post("/api/v1/professionals/register", json=professional_data)
        professional_id = register_response.json()["id"]
        
        # Try to access protected endpoints without auth header
        endpoints = [
            f"/api/v1/professionals/{professional_id}",
            f"/api/v1/professionals/mobile/{professional_data['mobile_number']}",
            "/api/v1/professionals/me"
        ]
        print('eeee')
        for endpoint in endpoints:
            response = client.get(endpoint)
            print(response.status_code)  # Debug output
            assert response.status_code == 403

    def test_invalid_token(self, client, setup_database, professional_data):
        """Test accessing protected endpoints with invalid token."""
        # Register professional to get a valid ID
        register_response = client.post("/api/v1/professionals/register", json=professional_data)
        professional_id = register_response.json()["id"]
        
        headers = {"Authorization": "Bearer invalid_token"}
        
        response = client.get(f"/api/v1/professionals/{professional_id}", headers=headers)
        assert response.status_code == 401


class TestTokenRefresh:
    """Test token refresh functionality."""

    def test_refresh_token_success(self, client, setup_database, professional_data):
        """Test successful token refresh."""
        # Register and login
        client.post("/api/v1/professionals/register", json=professional_data)
        
        login_data = {
            "identifier": professional_data["mobile_number"],
            "password": professional_data["password"]
        }
        login_response = client.post("/api/v1/professionals/login", json=login_data)
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        refresh_data = {"refresh_token": refresh_token}
        response = client.post("/api/v1/professionals/refresh-token", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client, setup_database):
        """Test token refresh with invalid refresh token."""
        refresh_data = {"refresh_token": "invalid_refresh_token"}
        response = client.post("/api/v1/professionals/refresh-token", json=refresh_data)
        
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]


class TestProfessionalNotFound:
    """Test 404 scenarios."""

    def test_get_nonexistent_professional_by_id(self, client, setup_database, professional_data):
        """Test getting non-existent professional by ID."""
        auth_data = TestProfessionalAuthentication().get_auth_headers(client, professional_data)
        headers = {"Authorization": auth_data["Authorization"]}
        
        # Try to get non-existent professional (ID 99999)
        response = client.get("/api/v1/professionals/99999", headers=headers)
        assert response.status_code == 403  # Will get 403 first due to authorization check

    def test_get_nonexistent_professional_by_mobile(self, client, setup_database, professional_data):
        """Test getting non-existent professional by mobile."""
        auth_data = TestProfessionalAuthentication().get_auth_headers(client, professional_data)
        headers = {"Authorization": auth_data["Authorization"]}
        
        response = client.get("/api/v1/professionals/mobile/+9999999999", headers=headers)
        assert response.status_code == 404
        assert "Professional not found" in response.json()["detail"]
