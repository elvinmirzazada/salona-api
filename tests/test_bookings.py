import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import BookingStatus, CustomerStatusType, StatusType
from app.models.models import Customers, Companies, Bookings, BookingServices, CategoryServices, CompanyCategories, Users


@pytest.fixture
def sample_company(setup_database):
    """Create a sample company for testing."""
    return {
        "id": str(uuid.uuid4()),
        "name": "Test Salon",
        "type": "Salon",
        "logo_url": "https://example.com/logo.png",
        "website": "https://testsalon.com",
        "description": "A test salon",
        "team_size": 5,
        "status": StatusType.active
    }


@pytest.fixture
def sample_user(setup_database):
    """Create a sample user for testing."""
    return {
        "id": str(uuid.uuid4()),
        "first_name": "John",
        "last_name": "Stylist",
        "email": "john.stylist@example.com",
        "password": "password123",  # Would be hashed in real application
        "phone": "+1234567890",
        "status": CustomerStatusType.active,
        "email_verified": True
    }


@pytest.fixture
def sample_customer(setup_database):
    """Create a sample customer for testing."""
    return {
        "id": str(uuid.uuid4()),
        "first_name": "Alice",
        "last_name": "Customer",
        "email": "alice.customer@example.com",
        "phone": "+0987654321",
        "password": "password456",  # Would be hashed in real application
        "status": CustomerStatusType.active
    }


@pytest.fixture
def sample_category(setup_database, db, sample_company):
    """Create a sample service category."""
    category = CompanyCategories(
        id=uuid.uuid4(),
        company_id=sample_company["id"],
        name="Haircuts",
        description="All types of haircuts"
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture
def sample_service(setup_database, db, sample_category):
    """Create a sample service."""
    service = CategoryServices(
        id=uuid.uuid4(),
        category_id=sample_category.id,
        name="Men's Haircut",
        duration=30,
        price=25,
        discount_price=20,
        status=StatusType.active
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@pytest.fixture
def setup_test_data(setup_database, db, sample_company, sample_user, sample_customer, sample_category, sample_service):
    """Setup all test data needed for booking tests."""
    # Create company
    company = Companies(**sample_company)
    db.add(company)
    
    # Create user (stylist)
    user = Users(**sample_user)
    db.add(user)
    
    # Create customer
    customer = Customers(**sample_customer)
    db.add(customer)
    
    db.commit()
    
    # Return all created entities for test use
    return {
        "company": company,
        "user": user,
        "customer": customer,
        "category": sample_category,
        "service": sample_service
    }


@pytest.fixture
def sample_booking(db, setup_test_data):
    """Create a sample booking."""
    start_time = datetime.now(timezone.utc) + timedelta(days=1)  # Tomorrow
    booking = Bookings(
        id=uuid.uuid4(),
        customer_id=setup_test_data["customer"].id,
        company_id=setup_test_data["company"].id,
        status=BookingStatus.SCHEDULED,
        start_at=start_time,
        end_at=start_time + timedelta(minutes=30),
        total_price=25,
        notes="Test booking"
    )
    db.add(booking)
    db.commit()
    
    # Add booking service
    booking_service = BookingServices(
        id=uuid.uuid4(),
        booking_id=booking.id,
        category_service_id=setup_test_data["service"].id,
        user_id=setup_test_data["user"].id,
        start_at=start_time,
        end_at=start_time + timedelta(minutes=30)
    )
    db.add(booking_service)
    db.commit()
    db.refresh(booking)
    
    return booking


@pytest.fixture
def auth_headers(setup_test_data):
    """Simulate auth headers for a company user."""
    # In a real test, you would generate a real token
    # Here we'll simulate the auth by mocking the dependency in tests
    return {"Authorization": f"Bearer company_token_{setup_test_data['company'].id}"}


class TestBookingEndpoints:
    """Tests for booking endpoints."""
    
    def test_create_booking(self, client, setup_test_data, db):
        """Test creating a new booking."""
        # Define the booking data
        start_time = datetime.now(timezone.utc) + timedelta(days=1)  # Tomorrow
        booking_data = {
            "company_id": str(setup_test_data["company"].id),
            "start_time": start_time.isoformat(),
            "services": [
                {
                    "category_service_id": str(setup_test_data["service"].id),
                    "user_id": str(setup_test_data["user"].id),
                    "notes": "Test service booking"
                }
            ],
            "notes": "Test booking notes",
            "customer_info": {
                "first_name": "New",
                "last_name": "Customer",
                "email": "new.customer@example.com",
                "phone": "+1122334455"
            }
        }
        
        # Make the request
        response = client.post("/api/v1/bookings", json=booking_data)
        
        # Assertions
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "data" in response_data
        assert response_data["data"]["notes"] == "Test booking notes"
        
        # Verify the booking was created in the database
        booking_id = response_data["data"]["id"]
        db_booking = db.query(Bookings).filter(Bookings.id == booking_id).first()
        assert db_booking is not None
        assert db_booking.notes == "Test booking notes"
        
        # Verify booking services were created
        booking_services = db.query(BookingServices).filter(BookingServices.booking_id == booking_id).all()
        assert len(booking_services) == 1
        
    def test_get_booking(self, client, sample_booking, auth_headers):
        """Test retrieving a booking by ID."""
        # Get the booking by ID
        response = client.get(f"/api/v1/bookings/{sample_booking.id}")
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["data"]["id"] == str(sample_booking.id)
        assert response_data["data"]["notes"] == "Test booking"
        
    def test_update_booking(self, client, sample_booking, auth_headers, db, monkeypatch):
        """Test updating a booking."""
        # Mock the get_current_company_id dependency
        def mock_get_company_id():
            return str(sample_booking.company_id)
            
        # Apply the mock
        from app.api.dependencies import get_current_company_id
        monkeypatch.setattr("app.api.api_v1.endpoints.bookings.get_current_company_id", mock_get_company_id)
        
        # Update data
        update_data = {
            "notes": "Updated booking notes",
            "status": "confirmed"
        }
        
        # Make the request
        response = client.put(f"/api/v1/bookings/{sample_booking.id}", json=update_data)
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["data"]["notes"] == "Updated booking notes"
        assert response_data["data"]["status"] == "confirmed"
        
        # Verify in database
        db.refresh(sample_booking)
        assert sample_booking.notes == "Updated booking notes"
        assert sample_booking.status == BookingStatus.CONFIRMED
        
    def test_cancel_booking(self, client, sample_booking, auth_headers, db, monkeypatch):
        """Test cancelling a booking."""
        # Mock the get_current_company_id dependency
        def mock_get_company_id():
            return str(sample_booking.company_id)
            
        # Apply the mock
        from app.api.dependencies import get_current_company_id
        monkeypatch.setattr("app.api.api_v1.endpoints.bookings.get_current_company_id", mock_get_company_id)
        
        # Make the request to cancel (delete endpoint)
        response = client.delete(f"/api/v1/bookings/{sample_booking.id}")
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["message"] == "Booking cancelled successfully"
        
        # Verify in database - should be marked as cancelled, not deleted
        db.refresh(sample_booking)
        assert sample_booking.status == BookingStatus.CANCELLED
        
    def test_confirm_booking(self, client, sample_booking, auth_headers, db, monkeypatch):
        """Test confirming a booking."""
        # Mock the get_current_company_id dependency
        def mock_get_company_id():
            return str(sample_booking.company_id)
            
        # Apply the mock
        from app.api.dependencies import get_current_company_id
        monkeypatch.setattr("app.api.api_v1.endpoints.bookings.get_current_company_id", mock_get_company_id)
        
        # Make the request to confirm
        response = client.post(f"/api/v1/bookings/{sample_booking.id}/confirm")
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["message"] == "Booking confirmed successfully"
        
        # Verify in database
        db.refresh(sample_booking)
        assert sample_booking.status == BookingStatus.CONFIRMED
