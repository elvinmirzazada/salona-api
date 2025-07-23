from fastapi import APIRouter
from app.api.api_v1.endpoints import professionals, businesses, services, clients, appointments

api_router = APIRouter()
api_router.include_router(professionals.router, prefix="/professionals", tags=["professionals"])
api_router.include_router(businesses.router, prefix="/businesses", tags=["businesses"])
api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
