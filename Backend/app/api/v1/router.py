from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    analytics,
    auth,
    berths,
    chat,
    congestion,
    eta,
    export,
    gdpr,
    health,
    import_,
    notifications,
    operations,
    optimization,
    port_ops,
    ports,
    predictions,
    vessels,
    visits,
    voyages,
    work_orders,
)

api_router = APIRouter(prefix="/api/v1")

# ── Authentication & IAM ──────────────────────────────────────────────────────
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# ── Core resources ────────────────────────────────────────────────────────────
api_router.include_router(health.router)
api_router.include_router(ports.router, prefix="/ports", tags=["Ports"])
api_router.include_router(vessels.router)
api_router.include_router(berths.router)
api_router.include_router(visits.router)
api_router.include_router(voyages.router, prefix="/voyages", tags=["Voyages"])
api_router.include_router(predictions.router)

# ── Operational intelligence ──────────────────────────────────────────────────
api_router.include_router(operations.router, prefix="/ops", tags=["Operations"])

# ── Work orders ───────────────────────────────────────────────────────────────
api_router.include_router(work_orders.router, tags=["Work Orders"])

# ── AI / predictions ──────────────────────────────────────────────────────────
api_router.include_router(eta.router, prefix="/ai", tags=["AI Predictions"])

# ── Port operations (Stage-2 berth optimizer) ─────────────────────────────────
api_router.include_router(port_ops.router, prefix="/port-ops", tags=["Port Operations"])

# ── Stage-3 congestion forecast ───────────────────────────────────────────────
api_router.include_router(congestion.router, prefix="/congestion", tags=["Congestion Forecast"])

# ── Optimization ──────────────────────────────────────────────────────────────
api_router.include_router(optimization.router, prefix="/opt", tags=["Optimization"])

# ── Analytics ─────────────────────────────────────────────────────────────────
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])

# ── Data import / export ──────────────────────────────────────────────────────
api_router.include_router(import_.router, prefix="/data", tags=["Data Import"])
api_router.include_router(export.router, prefix="/data", tags=["Data Export"])

# ── Notifications ─────────────────────────────────────────────────────────────
api_router.include_router(notifications.router, tags=["Notifications"])

# ── Privacy & GDPR ────────────────────────────────────────────────────────────
api_router.include_router(gdpr.router)

# ── System administration ─────────────────────────────────────────────────────
api_router.include_router(admin.router)

# ── AI Chatbot ────────────────────────────────────────────────────────────────
api_router.include_router(chat.router, prefix="/chat", tags=["AI Chatbot"])
