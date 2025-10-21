from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    
    PROJECT_NAME: str = "Salona Business API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_DB: str
    DATABASE_URL: Optional[str] = None
    SECRET_KEY: Optional[str] = None
    #
    # class Config:
    #     env_file = ".env"

    def _build_database_url(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    # Map Railway defaults
    @property
    def database_url(self):
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

    @classmethod
    def from_railway(cls):
        """Initialize using Railway's default variable names"""
        import os
        return cls(
            POSTGRES_USER=os.getenv("POSTGRES_USER"),
            POSTGRES_PASSWORD=os.getenv("POSTGRES_PASSWORD"),
            POSTGRES_SERVER=os.getenv("POSTGRES_SERVER"),
            POSTGRES_DB=os.getenv("POSTGRES_DB"),
        )

settings = Settings()
# settings.DATABASE_URL = settings._build_database_url()