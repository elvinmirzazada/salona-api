from fastapi import FastAPI
from app.core.config import settings
from app.api.api_v1.api import api_router
from starlette.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS settings
origins = [
    "http://0.0.0.0:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://0.0.0.0:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://192.168.8.5:3001",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8010",
    "http://127.0.0.1:8010",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-CSRFToken"  # Added CSRF token header
    ],
    expose_headers=["*"],
    max_age=600  # Cache preflight requests for 10 minutes
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to Salona Business API"}
