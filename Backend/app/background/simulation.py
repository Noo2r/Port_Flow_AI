"""
Background simulation removed.
All vessel state changes must come from real AIS data or manual operator input.
"""
import asyncio
from app.core.logging_config import logger


async def run_simulation() -> None:
    """No-op — simulation disabled. Real data only."""
    logger.info("Background simulation is disabled — real data mode")
    while True:
        await asyncio.sleep(3600)
