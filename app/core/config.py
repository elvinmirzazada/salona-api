from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    
    PROJECT_NAME: str = "Salona Business API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_USER: str = ''
    POSTGRES_PASSWORD: str = ''
    POSTGRES_SERVER: str = ''
    POSTGRES_DB: str = ''
    DATABASE_URL: Optional[str] = None
    SECRET_KEY: Optional[str] = None
    REDIS_URL: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_API_KEY: Optional[str] = None
    API_URL: str = "https://api.salona.me"
    FRONTEND_URL: str = "https://salona.me"

    # SMTP Email Configuration
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "Salona"
    MAILERSEND_API_KEY: Optional[str] = None
    MAILERSEND_FROM_EMAIL: Optional[str] = None
    MAILERSEND_FROM_NAME: str = "Salona"

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION_NAME: Optional[str] = None
    AWS_S3_BUCKET_NAME: Optional[str] = None

    class Config:
        env_file = ".env"  # only used locally if no system env vars are set
        env_file_encoding = "utf-8"
        extra = "ignore"  # ignore extra env vars Railway injects

    # Map Railway defaults
    def get_database_url(self):
        return self.DATABASE_URL or f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    def get_async_database_url(self):
        """Return async PostgreSQL URL for asyncpg driver"""
        if self.DATABASE_URL:
            # Replace postgresql:// with postgresql+asyncpg://
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"


settings = Settings()
# settings.DATABASE_URL = settings._build_database_url()