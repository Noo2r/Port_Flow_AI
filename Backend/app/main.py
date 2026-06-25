import asyncio
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.config import settings
from app.core.logging_config import logger, setup_logging
from app.core.redis_client import close_redis, get_redis
from app.database import AsyncSessionLocal
from app.middleware.audit_middleware import AuditTrailMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    setup_logging()
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # Connect to Redis (graceful if unavailable)
    await get_redis()

    # Seed default data
    from app.db.seed import seed_defaults
    async with AsyncSessionLocal() as db:
        await seed_defaults(db)

    # Reconcile berth occupancy — corrects any berth left OCCUPIED with no
    # active visit (e.g. a backup/restore captured mid-session). Safe to run
    # on every boot; it only ever releases false-OCCUPIED berths.
    from app.services.berth_reconciliation import reconcile_berth_occupancy
    async with AsyncSessionLocal() as db:
        recon_result = await reconcile_berth_occupancy(db)
        if recon_result["released"]:
            logger.info("Berth occupancy reconciliation at startup: %s", recon_result)

    # Initialise Stage-2 berth optimizer (loads CSV registry)
    try:
        from app.services import berth_service  # noqa: F401 — triggers module-level init
        from app.services.berth_service import get_berth_registry
        logger.info("Berth optimizer ready — %d berths loaded", len(get_berth_registry()))
    except Exception as _berth_exc:
        logger.warning("Berth optimizer init warning: %s", _berth_exc)

    # Launch background simulation
    from app.background.simulation import run_simulation
    sim_task = asyncio.create_task(run_simulation())
    logger.info("Background simulation task started")

    # Launch background maintenance (log retention + notification flush)
    maintenance_task = asyncio.create_task(_maintenance_loop())
    logger.info("Background maintenance task started")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    sim_task.cancel()
    maintenance_task.cancel()
    try:
        await asyncio.gather(sim_task, maintenance_task, return_exceptions=True)
    except asyncio.CancelledError:
        pass

    await close_redis()
    logger.info("Shutdown complete")


async def _maintenance_loop() -> None:
    """
    Background maintenance loop — runs every 6 hours:
    1. Flush pending notifications
    2. Purge expired audit logs (monthly check)
    3. Sweep expired berth allocations (time-based backstop — the primary
       trigger is row-count-based, see app/services/berth_service.py)
    4. Reconcile berth occupancy — self-heal any berth left OCCUPIED with
       no active visit (defense in depth alongside the startup check and
       the eta.py reassignment fix)
    """
    import calendar
    from datetime import datetime, timezone

    tick = 0
    while True:
        await asyncio.sleep(6 * 3600)  # every 6 hours
        tick += 1
        try:
            async with AsyncSessionLocal() as db:
                # Flush pending notifications every tick
                from app.services.notification_service import flush_pending_notifications
                result = await flush_pending_notifications(db)
                if result["sent"] + result["failed"] > 0:
                    logger.info("Notification flush: %s", result)

                # Purge old audit logs once per day (every 4 ticks)
                if tick % 4 == 0:
                    from app.services.gdpr_service import purge_old_audit_logs
                    deleted = await purge_old_audit_logs(db, settings.LOG_RETENTION_MONTHS)
                    if deleted:
                        logger.info("Log retention: purged %d old audit records", deleted)

                # Self-heal any berth left OCCUPIED with no active visit
                from app.services.berth_reconciliation import reconcile_berth_occupancy
                recon_result = await reconcile_berth_occupancy(db)
                if recon_result["released"]:
                    logger.info("Berth occupancy reconciliation: %s", recon_result)

            # Backstop sweep for expired berth allocations — covers
            # low-traffic sessions that never hit the 200-row trigger.
            from app.services.berth_service import clear_expired_allocations
            cleanup_result = clear_expired_allocations()
            if cleanup_result["removed"]:
                logger.info("Berth allocation backstop cleanup: %s", cleanup_result)

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Maintenance loop error: %s", exc)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "**PortFlow AI** — Production-grade async port operations Decision Support System.\n\n"
        "### Features\n"
        "- 🔐 **JWT Authentication** with refresh tokens, API keys, and RBAC\n"
        "- 🚢 **Vessel & Port Management** — full registry with IMO, dimensions, certificates\n"
        "- 📋 **Operations** — visit tracking, AIS updates, conflict detection\n"
        "- 🤖 **AI/Analytics** — ETA prediction, berth optimization, KPI dashboards\n"
        "- 📦 **Cargo** — manifest import, container tracking, bulk cargo\n"
        "- 🔧 **Work Orders** — auto-generated on berth assignment\n"
        "- 📨 **Notifications** — email, in-app, webhook delivery\n"
        "- 📊 **Export** — CSV & PDF reports for vessels, visits, KPIs\n"
        "- 📥 **Import** — bulk CSV/XLSX upload for vessels, visits, cargo\n"
        "- 🔒 **GDPR** — right to erasure, data portability, audit trail\n"
        "- 🗄️ **Backups** — automated pg_dump with optional S3 upload\n"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware stack (order matters — outermost first) ────────────────────────

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit trail — automatically records all mutating operations
app.add_middleware(AuditTrailMiddleware)


# ── Request logging middleware ────────────────────────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "%s %s → %d | %.1fms | req_id=%s",
        request.method, request.url.path, response.status_code, duration_ms, request_id,
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed",
            "details": exc.errors(),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Kubernetes-style readiness probe — verifies DB connectivity."""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "database": str(exc)},
        )
