import sys
import os
from pathlib import Path

# Add the parent directory to Python path so we can import app modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base_class import Base
from app.db.session import get_db

# Test database setup
SQLITE_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLITE_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture(scope="function")
def setup_database():
    """Create test database tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Create a new session to ensure no cached data remains
    db = TestingSessionLocal()
    try:
        db.execute(text("VACUUM"))  # Clean up the SQLite database
    finally:
        db.close()

@pytest.fixture(scope="module")
def setup_database_module():
    """Create test database tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Create a new session to ensure no cached data remains
    db = TestingSessionLocal()
    try:
        db.execute(text("VACUUM"))  # Clean up the SQLite database
    finally:
        db.close()

@pytest.fixture
def professional_data():
    """Sample professional data for testing."""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "mobile_number": "+1234567890",
        "password": "testpassword123",
        "country": "USA",
        "accept_privacy_policy": True
    }

@pytest.fixture
def another_professional_data():
    """Another sample professional data for testing."""
    return {
        "first_name": "Jane",
        "last_name": "Smith",
        "mobile_number": "+0987654321",
        "password": "anotherpassword123",
        "country": "Canada",
        "accept_privacy_policy": True
    }
