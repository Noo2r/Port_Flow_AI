from fastapi import APIRouter

from app.api.v1.endpoints import health, vessels, berths, visits, predictions

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(vessels.router)
api_router.include_router(berths.router)
api_router.include_router(visits.router)
api_router.include_router(predictions.router)
