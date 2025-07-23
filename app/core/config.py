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
    class Config:
        env_file = ".env"

    def _build_database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

settings = Settings()
# settings.DATABASE_URL = settings._build_database_url()