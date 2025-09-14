from fastapi import APIRouter
from app.api.api_v1.endpoints import customers, users

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(businesses.router, prefix="/businesses", tags=["businesses"])
# api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
# api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
