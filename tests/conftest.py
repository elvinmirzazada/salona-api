import sys
import os
from pathlib import Path
import uuid

# Add the parent directory to Python path so we can import app modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, event, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy.types import TypeDecorator

from app.main import app
from app.db.base_class import Base
from app.db.session import get_db

# Define a custom UUID type for SQLite
class SQLiteUUID(TypeDecorator):
    impl = BLOB
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            try:
                value = uuid.UUID(value)
            except (TypeError, ValueError):
                return None
        return value.bytes

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(bytes=value)

# Register the UUID type mapping for SQLite
from sqlalchemy import types
import sqlalchemy
sqlalchemy.dialects.sqlite.pysqlite.dialect.ischema_names['uuid'] = SQLiteUUID

# Test database setup
SQLITE_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLITE_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

# Register UUID converter for SQLite
@event.listens_for(engine, "connect")
def do_connect(dbapi_connection, connection_record):
    def adapt_uuid(uuid_obj):
        return uuid_obj.bytes if uuid_obj is not None else None

    def convert_uuid(blob):
        return uuid.UUID(bytes=blob) if blob is not None else None

    # Register the adapter and converter
    dbapi_connection.create_function("uuid_to_blob", 1, adapt_uuid)
    dbapi_connection.create_function("blob_to_uuid", 1, convert_uuid)

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
    # Create TestClient using the newer approach that works with latest httpx
    test_client = httpx.Client(transport=httpx.ASGITransport(app=app), base_url="http://test")

    yield test_client

@pytest.fixture
def db():
    """Get a testing database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def setup_database():
    """Create test database tables before each test and drop them after."""
    # Drop all tables first to ensure clean state
    Base.metadata.drop_all(bind=engine)
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after tests
    Base.metadata.drop_all(bind=engine)
    # Clean up the SQLite database
    db = TestingSessionLocal()
    try:
        db.execute(text("VACUUM"))
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
