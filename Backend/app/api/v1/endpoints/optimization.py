from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.optimization import OptimizationResult
from app.services.berth_optimizer import optimize_berth_assignments

router = APIRouter()


@router.post("/optimize", response_model=OptimizationResult)
async def run_berth_optimization(db: AsyncSession = Depends(get_db)):
    """
    Greedy berth assignment: assigns all unassigned SCHEDULED visits
    to available berths sorted by ETA and berth priority.
    """
    return await optimize_berth_assignments(db)
