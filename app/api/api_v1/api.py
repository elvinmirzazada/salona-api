from fastapi import APIRouter
from app.api.api_v1.endpoints import customers, users, companies, services, bookings, notifications

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

