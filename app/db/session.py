from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create engine with timezone configuration
engine = create_engine(
    settings.get_database_url(),
    connect_args={"options": "-c timezone=utc"} if "postgresql" in settings.get_database_url() else {}
)

# For PostgreSQL, ensure timezone is set to UTC at connection level
@event.listens_for(engine, "connect")
def set_timezone(dbapi_conn, connection_record):
    """Set timezone to UTC for each new database connection"""
    if "postgresql" in settings.get_database_url():
        cursor = dbapi_conn.cursor()
        cursor.execute("SET TIME ZONE 'UTC'")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()