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

    class Config:
        env_file = ".env"  # only used locally if no system env vars are set
        env_file_encoding = "utf-8"
        extra = "ignore"  # ignore extra env vars Railway injects

    # Map Railway defaults
    def get_database_url(self):
        return self.DATABASE_URL or f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"


settings = Settings()
# settings.DATABASE_URL = settings._build_database_url()