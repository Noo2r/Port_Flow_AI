"""
AI Chatbot Endpoint — PortFlow AI
===================================
Claude-powered assistant with tool calling for live port data.
Falls back to rule-based responses when ANTHROPIC_API_KEY is not set.

Routes (registered under /api/v1/chat):
    POST /message     → Process a user message, return AI response
    GET  /suggestions → Contextual quick-start questions
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.berth import Berth, BerthStatus
from app.models.iam import User
from app.models.notifications import Notification, NotificationStatus
from app.models.vessel import Vessel, VesselStatus, VesselType
from app.models.visit import ACTIVE_VISIT_STATUSES, Visit, VisitStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# Canonical definition lives in app.models.visit.ACTIVE_VISIT_STATUSES —
# shared with analytics.py, port_ops.py, and analytics_service.py. Previously
# this endpoint counted SCHEDULED visits as "active", which caused the
# chatbot's reported vessel counts to disagree with the Dashboard.
ACTIVE_STATUSES = ACTIVE_VISIT_STATUSES

# ── Request / Response schemas ────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str

class MessageRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []

class ChatResponse(BaseModel):
    response: str
    data: Optional[dict] = None
    suggested_questions: list[str] = []
    tool_calls_made: list[str] = []
    model_used: str = "fallback"

# ── Claude tool definitions ───────────────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "name": "get_port_kpis",
        "description": (
            "Retrieve current port Key Performance Indicators: active vessel count, "
            "average waiting time, berth utilization percentage, conflict count, and "
            "throughput totals. Use for any question about port performance, statistics, "
            "or operational overview."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_berth_status",
        "description": (
            "Get real-time occupancy and capability data for berths. "
            "Returns status (AVAILABLE/OCCUPIED/MAINTENANCE), utilization rate, max "
            "dimensions, and crane availability. Use for berth availability, highest "
            "utilization, or specific berth queries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "berth_code": {
                    "type": "string",
                    "description": "Specific berth code e.g. 'A1', 'B3'. Omit for all berths.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "list_vessels",
        "description": (
            "List vessels in the fleet with optional filters. Use for fleet overview, "
            "finding vessels by type or status, or searching by name."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["at_sea", "approaching", "anchored", "berthed", "departed"],
                    "description": "Filter by vessel operational status.",
                },
                "vessel_type": {
                    "type": "string",
                    "enum": ["container", "bulk_carrier", "tanker", "ro_ro", "general_cargo", "other"],
                    "description": "Filter by vessel type.",
                },
                "search_name": {
                    "type": "string",
                    "description": "Partial vessel name search (case-insensitive).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 20, max 50).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "list_upcoming_arrivals",
        "description": (
            "Get vessels expected to arrive within the next N hours. "
            "Use for questions like 'arriving today', 'ships expected tomorrow', "
            "or 'upcoming arrivals'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hours_ahead": {
                    "type": "integer",
                    "description": "Forecast window in hours (default 24, max 72).",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_congestion_forecast",
        "description": (
            "Run the AI congestion model against current port state and return a "
            "forecast for the next N hours. Includes congestion level (Low/Medium/High/Critical), "
            "berth occupancy, queue length, and hourly trend. Use for any congestion or "
            "traffic-level question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Forecast horizon: 24, 48, or 72 hours (default 48).",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_port_allocations",
        "description": (
            "Return the current berth allocation schedule: which vessel is assigned to "
            "which berth, waiting times, and conflict flags. "
            "Use for scheduling, conflict detection, or specific berth assignments."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "include_completed": {
                    "type": "boolean",
                    "description": "Include recently completed visits (default false).",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_vessel_history",
        "description": (
            "Get detailed information and visit history for a specific vessel. "
            "Use to explain delays, check a vessel's operational patterns, or "
            "answer 'why is vessel X delayed'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "vessel_name": {
                    "type": "string",
                    "description": "Vessel name (partial match supported).",
                },
                "vessel_id": {
                    "type": "integer",
                    "description": "Exact vessel ID if known.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_analytics",
        "description": (
            "Get port analytics: vessel type distribution, visit status breakdown, "
            "and average waiting times per vessel type. "
            "Use for trend analysis or performance comparisons."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "enum": ["throughput", "waiting_time", "berth_utilization", "vessel_types", "all"],
                    "description": "Which metric set to retrieve (default 'all').",
                }
            },
            "required": [],
        },
    },
    {
        "name": "list_notifications",
        "description": (
            "Retrieve recent system alerts and notifications. "
            "Use for questions about warnings, incidents, or recent system events."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent notifications to return (default 10, max 25).",
                }
            },
            "required": [],
        },
    },
]

# ── System prompt ─────────────────────────────────────────────────────────────

def _system_prompt() -> str:
    return f"""You are PortFlow AI Assistant — the intelligent operations officer for a Smart Port Decision Support System. \
You help port managers, vessel agents, and operations staff make fast, data-driven decisions.

You have real-time access to port data through tools:
• Port KPIs — utilization %, waiting times, conflict rates, throughput
• Berth status — per-berth occupancy, dimensions, crane availability
• Vessel fleet — search by name, type, or status
• Upcoming arrivals — ETA list for next 24–72 hours
• AI congestion forecast — 24/48/72-hour prediction with confidence
• Berth allocation schedule — assignments, wait times, conflict flags
• Vessel history — per-vessel delay patterns and visit records
• Analytics — type distribution, trend metrics
• System notifications — recent alerts and warnings

Response rules:
1. Always call the relevant tool(s) before answering — never guess live data.
2. Present multi-row results as markdown tables with clear headers.
3. Use ✅ good, ⚠️ moderate issue, ❌ critical problem.
4. Include units: min, h, %, kn, m, TEU.
5. Cite data timestamp for live metrics.
6. For delay / congestion questions, identify likely contributing factors from the data.
7. Keep responses concise — operators need quick answers.

Current UTC: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"""

# ── Tool implementations (direct DB — no internal HTTP) ───────────────────────

async def _kpis(db: AsyncSession) -> dict:
    active_q = await db.execute(
        select(func.count()).select_from(Visit).where(Visit.status.in_(ACTIVE_STATUSES))
    )
    active = int(active_q.scalar() or 0)

    total_q  = await db.execute(select(func.count()).select_from(Visit))
    total    = int(total_q.scalar() or 0)

    done_q   = await db.execute(select(func.count()).select_from(Visit).where(Visit.status == VisitStatus.COMPLETED))
    done     = int(done_q.scalar() or 0)

    if active > 0:
        kpi_f = Visit.status.in_(ACTIVE_STATUSES)
    else:
        recent = (
            select(Visit.id).where(Visit.status == VisitStatus.COMPLETED)
            .order_by(desc(Visit.ata)).limit(500).scalar_subquery()
        )
        kpi_f = Visit.id.in_(recent)

    wait_q  = await db.execute(
        select(func.avg(Visit.waiting_time_hours)).where(
            kpi_f, Visit.waiting_time_hours.isnot(None), Visit.waiting_time_hours <= 24
        )
    )
    avg_w = float(wait_q.scalar() or 0)

    conf_q  = await db.execute(
        select(func.count()).select_from(Visit).where(kpi_f, Visit.waiting_time_hours > 1.5, Visit.waiting_time_hours <= 24)
    )
    conflicts = int(conf_q.scalar() or 0)

    den_q   = await db.execute(select(func.count()).select_from(Visit).where(kpi_f))
    denom   = int(den_q.scalar() or 1)

    bt_q    = await db.execute(select(func.count()).select_from(Berth))
    total_b = int(bt_q.scalar() or 1)

    occ_q   = await db.execute(select(func.count()).select_from(Berth).where(Berth.status == BerthStatus.OCCUPIED))
    occ     = int(occ_q.scalar() or 0)

    if active == 0:
        svc_q  = await db.execute(select(func.avg(Visit.berth_time_hours)).where(kpi_f, Visit.berth_time_hours.isnot(None)))
        avg_svc = float(svc_q.scalar() or 12)
        util_pct = round(min(99, avg_svc / 24 * 100), 1)
    else:
        util_pct = round(occ / total_b * 100, 1)

    return {
        "active_vessels": active,
        "total_visits": total,
        "completed_visits": done,
        "avg_waiting_time_minutes": round(avg_w * 60, 1),
        "berth_utilization_pct": util_pct,
        "occupied_berths": occ,
        "total_berths": total_b,
        "conflict_count": conflicts,
        "conflict_rate_pct": round(conflicts / denom * 100, 1),
        "timestamp": datetime.utcnow().isoformat(),
    }


async def _berth_status(db: AsyncSession, berth_code: Optional[str] = None) -> dict:
    q = select(Berth).order_by(Berth.code)
    if berth_code:
        q = q.where(Berth.code == berth_code.upper())
    rows    = (await db.execute(q)).scalars().all()
    berths  = [
        {
            "code":        b.code,
            "name":        b.name,
            "type":        b.berth_type.value if b.berth_type else "unknown",
            "status":      b.status.value,
            "max_length_m": b.max_length,
            "max_draft_m": b.max_draft,
            "has_crane":   b.has_crane,
        }
        for b in rows
    ]
    occ = sum(1 for b in berths if b["status"] == "occupied")
    avl = sum(1 for b in berths if b["status"] == "available")
    return {
        "berths": berths,
        "summary": {
            "total": len(berths),
            "occupied": occ,
            "available": avl,
            "in_maintenance": len(berths) - occ - avl,
            "utilization_pct": round(occ / len(berths) * 100, 1) if berths else 0,
        },
    }


async def _list_vessels(
    db: AsyncSession,
    status: Optional[str] = None,
    vessel_type: Optional[str] = None,
    search_name: Optional[str] = None,
    limit: int = 20,
) -> dict:
    q = select(Vessel)
    if status:
        try:
            q = q.where(Vessel.status == VesselStatus(status))
        except ValueError:
            pass
    if vessel_type:
        try:
            q = q.where(Vessel.vessel_type == VesselType(vessel_type))
        except ValueError:
            pass
    if search_name:
        q = q.where(Vessel.name.ilike(f"%{search_name}%"))
    q = q.limit(min(limit, 50))
    rows = (await db.execute(q)).scalars().all()
    return {
        "count": len(rows),
        "vessels": [
            {
                "id":           v.id,
                "name":         v.name,
                "imo":          v.imo_number,
                "type":         v.vessel_type.value,
                "status":       v.status.value,
                "flag":         v.flag,
                "loa_m":        v.length_overall,
                "gross_tonnage": v.gross_tonnage,
                "operator":     v.operator,
            }
            for v in rows
        ],
    }


async def _upcoming_arrivals(db: AsyncSession, hours_ahead: int = 24) -> dict:
    now     = datetime.utcnow()
    cutoff  = now + timedelta(hours=min(hours_ahead, 72))
    rows    = (
        await db.execute(
            select(Visit)
            .where(
                Visit.status.in_([VisitStatus.SCHEDULED, VisitStatus.APPROACHING]),
                Visit.eta.isnot(None),
                Visit.eta >= now,
                Visit.eta <= cutoff,
            )
            .order_by(Visit.eta)
            .limit(25)
        )
    ).scalars().all()

    arrivals = []
    for v in rows:
        vessel = await db.get(Vessel, v.vessel_id) if v.vessel_id else None
        berth  = await db.get(Berth,  v.berth_id)  if v.berth_id  else None
        diff_s = (v.eta - now).total_seconds() if v.eta else 0
        arrivals.append({
            "vessel":   vessel.name if vessel else "Unknown",
            "type":     vessel.vessel_type.value if vessel else None,
            "eta":      v.eta.isoformat() if v.eta else None,
            "eta_in":   f"{int(diff_s//3600)}h {int((diff_s%3600)//60)}m",
            "berth":    berth.code if berth else "TBD",
            "status":   v.status.value,
            "cargo":    v.cargo_type,
            "wait_h":   v.waiting_time_hours,
        })
    return {
        "horizon_hours": hours_ahead,
        "count":         len(arrivals),
        "arrivals":      arrivals,
        "as_of":         now.isoformat(),
    }


async def _congestion_forecast(db: AsyncSession, hours: int = 48) -> dict:
    """
    Single source of truth (Phase 4.5, Task 5): this no longer runs its own
    independent congestion calculation. It calls the exact same
    app.services.congestion_service.get_port_congestion_forecasts() used by
    GET /api/v1/congestion/port-overview, then summarizes across ports for a
    system-wide "current" view — so the AI Assistant's answer can never
    disagree with the Congestion Forecast page for the same moment in time.
    """
    from app.services.congestion_service import get_port_congestion_forecasts

    active_q = await db.execute(
        select(func.count()).select_from(Visit).where(Visit.status.in_(ACTIVE_STATUSES))
    )
    active = int(active_q.scalar() or 0)

    bt_q    = await db.execute(select(func.count()).select_from(Berth))
    total_b = int(bt_q.scalar() or 1)

    occ_q   = await db.execute(select(func.count()).select_from(Berth).where(Berth.status == BerthStatus.OCCUPIED))
    occ     = int(occ_q.scalar() or 0)

    per_port = await get_port_congestion_forecasts(db)
    if per_port:
        # System-wide level = the busiest port's level (the operationally
        # meaningful "should I be worried right now" answer), index/queue/
        # confidence = mean across ports — all real, all from the same
        # per-port forecasts the Congestion Forecast page shows.
        order = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
        busiest = max(per_port, key=lambda p: order.get(p["congestion_label"], 0))
        level      = busiest["congestion_label"]
        level_val  = sum(p["congestion_level"] for p in per_port) / len(per_port)
        queue_pred = round(sum(p["queue_length"] for p in per_port) / len(per_port))
        confidence = sum(p["confidence"] for p in per_port) / len(per_port)
    else:
        # No ports / model unavailable — fall back to a coarse DB-only
        # heuristic rather than failing the whole chat response.
        congestion_idx = min(1.0, occ / max(total_b, 1))
        queue_pred = max(0, active - occ)
        confidence = 0.6
        if congestion_idx > 0.80:
            level, level_val = "Critical", 0.90
        elif congestion_idx > 0.60:
            level, level_val = "High",     0.70
        elif congestion_idx > 0.35:
            level, level_val = "Medium",   0.45
        else:
            level, level_val = "Low",      0.20

    # Hourly trend
    steps    = max(6, min(hours, 72))
    step_h   = hours // steps
    forecast = []
    for i in range(steps + 1):
        fh  = i * step_h
        fhr = (datetime.utcnow().hour + fh) % 24
        tf  = 1.15 if 8 <= fhr <= 18 else 0.85
        fi  = round(min(1.0, level_val * tf * (1 + fh * 0.003)), 3)
        fl  = ("Critical" if fi > 0.75 else "High" if fi > 0.55 else "Medium" if fi > 0.30 else "Low")
        forecast.append({
            "hours_from_now":  fh,
            "time":            (datetime.utcnow() + timedelta(hours=fh)).strftime("%H:%M UTC"),
            "level":           fl,
            "index":           fi,
        })

    return {
        "current": {
            "level":             level,
            "index":             round(level_val, 3),
            "active_vessels":    active,
            "occupied_berths":   occ,
            "total_berths":      total_b,
            "occupancy_pct":     round(occ / max(total_b, 1) * 100, 1),
            "queue_length":      queue_pred,
            "confidence":        round(confidence, 2),
        },
        "forecast_hours": hours,
        "hourly_trend":   forecast,
        "generated_at":   datetime.utcnow().isoformat(),
    }


async def _allocations(db: AsyncSession, include_completed: bool = False) -> dict:
    if not include_completed:
        q = select(Visit).where(Visit.status.in_(ACTIVE_STATUSES)).order_by(Visit.eta)
    else:
        q = select(Visit).order_by(desc(Visit.ata)).limit(50)

    rows  = (await db.execute(q)).scalars().all()
    items = []
    cfls  = 0
    for v in rows:
        vessel = await db.get(Vessel, v.vessel_id) if v.vessel_id else None
        berth  = await db.get(Berth,  v.berth_id)  if v.berth_id  else None
        wh     = min(float(v.waiting_time_hours or 0), 24.0)
        wm     = round(wh * 60)
        has_c  = wm > 90
        if has_c:
            cfls += 1
        items.append({
            "vessel":     vessel.name if vessel else "Unknown",
            "berth":      berth.code  if berth  else "TBD",
            "status":     v.status.value,
            "eta":        v.eta.isoformat() if v.eta else None,
            "wait_min":   wm,
            "conflict":   has_c,
            "cargo":      v.cargo_type,
        })
    return {"count": len(items), "conflict_count": cfls, "allocations": items}


async def _vessel_history(
    db: AsyncSession,
    vessel_name: Optional[str] = None,
    vessel_id:   Optional[int] = None,
) -> dict:
    vessel = None
    if vessel_id:
        vessel = await db.get(Vessel, vessel_id)
    elif vessel_name:
        r = await db.execute(select(Vessel).where(Vessel.name.ilike(f"%{vessel_name}%")).limit(1))
        vessel = r.scalars().first()

    if not vessel:
        return {"error": f"Vessel not found: {vessel_name or vessel_id}"}

    visits = (
        await db.execute(
            select(Visit).where(Visit.vessel_id == vessel.id)
            .order_by(desc(Visit.eta)).limit(10)
        )
    ).scalars().all()

    history = []
    for v in visits:
        berth = await db.get(Berth, v.berth_id) if v.berth_id else None
        wh    = float(v.waiting_time_hours or 0)
        delay = (
            f"Significant: {round(wh,1)}h wait" if wh > 2
            else f"Minor: {round(wh*60)}min wait" if wh > 1
            else "On schedule"
        )
        history.append({
            "visit_id": v.id,
            "status":   v.status.value,
            "eta":      v.eta.isoformat() if v.eta else None,
            "ata":      v.ata.isoformat() if v.ata else None,
            "berth":    berth.code if berth else "N/A",
            "wait_h":   round(wh, 2),
            "delay":    delay,
            "cargo":    v.cargo_type,
        })

    delays = [v.waiting_time_hours for v in visits if v.waiting_time_hours and v.waiting_time_hours <= 24]
    avg_d  = sum(delays) / len(delays) if delays else 0

    return {
        "vessel": {
            "id": vessel.id, "name": vessel.name, "imo": vessel.imo_number,
            "type": vessel.vessel_type.value, "status": vessel.status.value,
            "operator": vessel.operator, "flag": vessel.flag,
            "loa_m": vessel.length_overall, "gross_tonnage": vessel.gross_tonnage,
        },
        "visit_history": history,
        "summary": {
            "total_visits":       len(visits),
            "avg_waiting_time_h": round(avg_d, 2),
            "delay_prone":        avg_d > 1.5,
        },
    }


async def _analytics(db: AsyncSession, metric: str = "all") -> dict:
    type_r = await db.execute(
        select(Vessel.vessel_type, func.count().label("n")).group_by(Vessel.vessel_type)
    )
    type_dist = {r.vessel_type.value: int(r.n) for r in type_r.mappings()}

    status_r = await db.execute(
        select(Visit.status, func.count().label("n")).group_by(Visit.status)
    )
    status_dist = {r.status.value: int(r.n) for r in status_r.mappings()}

    wait_r = await db.execute(
        select(Vessel.vessel_type, func.avg(Visit.waiting_time_hours).label("avg"))
        .join(Visit, Visit.vessel_id == Vessel.id)
        .where(Visit.waiting_time_hours.isnot(None), Visit.waiting_time_hours <= 24)
        .group_by(Vessel.vessel_type)
    )
    wait_by_type = {r.vessel_type.value: round(float(r.avg) * 60, 1) for r in wait_r.mappings()}

    total_v_r = await db.execute(select(func.count()).select_from(Vessel))
    total_v   = int(total_v_r.scalar() or 0)

    return {
        "total_vessels":               total_v,
        "vessel_type_distribution":    type_dist,
        "visit_status_distribution":   status_dist,
        "avg_wait_minutes_by_type":    wait_by_type,
        "generated_at":                datetime.utcnow().isoformat(),
    }


async def _notifications(db: AsyncSession, limit: int = 10) -> dict:
    rows = (
        await db.execute(
            select(Notification)
            .order_by(desc(Notification.created_at))
            .limit(min(limit, 25))
        )
    ).scalars().all()
    return {
        "count": len(rows),
        "notifications": [
            {
                "id":         n.id,
                "recipient":  n.recipient,
                "subject":    n.subject,
                "body":       n.body[:200] if n.body else None,
                "channel":    n.channel.value if n.channel else None,
                "status":     n.status.value if n.status else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in rows
        ],
    }

# ── Tool dispatcher ───────────────────────────────────────────────────────────

async def _dispatch(name: str, args: dict, db: AsyncSession) -> Any:
    try:
        if name == "get_port_kpis":
            return await _kpis(db)
        if name == "get_berth_status":
            return await _berth_status(db, args.get("berth_code"))
        if name == "list_vessels":
            return await _list_vessels(
                db,
                status=args.get("status"),
                vessel_type=args.get("vessel_type"),
                search_name=args.get("search_name"),
                limit=args.get("limit", 20),
            )
        if name == "list_upcoming_arrivals":
            return await _upcoming_arrivals(db, hours_ahead=args.get("hours_ahead", 24))
        if name == "get_congestion_forecast":
            return await _congestion_forecast(db, hours=args.get("hours", 48))
        if name == "get_port_allocations":
            return await _allocations(db, include_completed=args.get("include_completed", False))
        if name == "get_vessel_history":
            return await _vessel_history(db, vessel_name=args.get("vessel_name"), vessel_id=args.get("vessel_id"))
        if name == "get_analytics":
            return await _analytics(db, metric=args.get("metric", "all"))
        if name == "list_notifications":
            return await _notifications(db, limit=args.get("limit", 10))
        return {"error": f"Unknown tool: {name}"}
    except Exception as exc:
        logger.error("Tool %s failed: %s", name, exc)
        return {"error": str(exc)}

# ── Suggested follow-up generator ─────────────────────────────────────────────

def _suggestions(message: str) -> list[str]:
    m = message.lower()
    if any(w in m for w in ["congestion", "traffic", "forecast"]):
        return ["Show 72-hour congestion forecast", "Which berths are most congested?", "How many vessels are queued?"]
    if any(w in m for w in ["berth", "dock", "pier"]):
        return ["Which berth has highest utilization?", "Show active berth allocations", "Are there maintenance berths?"]
    if any(w in m for w in ["arriv", "tomorrow", "today", "expected", "coming"]):
        return ["Show vessels arriving in 48 hours", "What's the congestion forecast?", "Which berths are available?"]
    if any(w in m for w in ["vessel", "ship", "fleet"]):
        return ["List vessels by type", "Which vessels are anchored?", "Find a specific vessel"]
    if any(w in m for w in ["kpi", "performance", "metric", "statistic"]):
        return ["Show analytics trends", "What is the conflict rate?", "Compare berth utilization by type"]
    if any(w in m for w in ["conflict", "delay", "wait"]):
        return ["Show all active conflicts", "Which vessels are delayed?", "What is the average wait today?"]
    return [
        "What are the current port KPIs?",
        "Show congestion forecast for 48 hours",
        "Which vessels are arriving today?",
    ]

# ── Rule-based fallback ───────────────────────────────────────────────────────

async def _fallback(message: str, db: AsyncSession) -> ChatResponse:
    m      = message.lower()
    used   = []

    if any(w in m for w in ["kpi", "performance", "metric", "overview", "status"]):
        d    = await _kpis(db); used.append("get_port_kpis")
        rows = (
            f"| Active Vessels | {d['active_vessels']} |\n"
            f"| Avg Wait | {d['avg_waiting_time_minutes']} min |\n"
            f"| Berth Utilization | {d['berth_utilization_pct']}% |\n"
            f"| Occupied / Total | {d['occupied_berths']} / {d['total_berths']} |\n"
            f"| Conflicts | {d['conflict_count']} ({d['conflict_rate_pct']}%) |"
        )
        text = f"**Port KPIs** · {d['timestamp'][:16]} UTC\n\n| Metric | Value |\n|--------|-------|\n{rows}"

    elif any(w in m for w in ["berth", "dock", "pier", "utiliz"]):
        d    = await _berth_status(db); used.append("get_berth_status")
        s    = d["summary"]
        rows = "\n".join(
            f"| {b['code']} | {b['type']} | {b['status'].upper()} | {'✅' if b['status']=='available' else '🔴' if b['status']=='occupied' else '🔧'} |"
            for b in d["berths"][:12]
        )
        text = (
            f"**Berth Status** — {s['occupied']}/{s['total']} occupied ({s['utilization_pct']}%)\n\n"
            f"| Code | Type | Status | | \n|------|------|--------|---|\n{rows}"
        )

    elif any(w in m for w in ["arriv", "tomorrow", "today", "coming", "expected", "eta"]):
        h    = 48 if "tomorrow" in m else 24
        d    = await _upcoming_arrivals(db, hours_ahead=h); used.append("list_upcoming_arrivals")
        if d["count"] == 0:
            text = f"No vessels expected in the next {h} hours."
        else:
            rows = "\n".join(
                f"| {a['vessel']} | {a['type'] or '—'} | {a['eta_in']} | {a['berth']} |"
                for a in d["arrivals"]
            )
            text = (
                f"**Upcoming Arrivals** (next {h}h) — {d['count']} vessel(s)\n\n"
                f"| Vessel | Type | ETA In | Berth |\n|--------|------|--------|-------|\n{rows}"
            )

    elif any(w in m for w in ["congestion", "traffic", "forecast", "predict"]):
        h    = 72 if "72" in m else 48 if "48" in m else 24
        d    = await _congestion_forecast(db, hours=h); used.append("get_congestion_forecast")
        cur  = d["current"]
        emoji = {"Low": "✅", "Medium": "⚠️", "High": "⚠️", "Critical": "❌"}.get(cur["level"], "ℹ️")
        rows = "\n".join(
            f"| +{f['hours_from_now']}h | {f['time']} | {f['level']} | {f['index']:.2f} |"
            for f in d["hourly_trend"][::max(1, len(d["hourly_trend"])//6)]
        )
        text = (
            f"**Congestion Forecast** ({h}h horizon)\n\n"
            f"**Now:** {emoji} **{cur['level']}** (index {cur['index']:.2f}, confidence {cur['confidence']:.0%})\n"
            f"- Active vessels: {cur['active_vessels']} | Occupied berths: {cur['occupied_berths']}/{cur['total_berths']}\n"
            f"- Queue: {cur['queue_length']} vessel(s) | Occupancy: {cur['occupancy_pct']}%\n\n"
            f"| Offset | Time | Level | Index |\n|--------|------|-------|-------|\n{rows}"
        )

    elif any(w in m for w in ["vessel", "ship", "fleet", "anchor"]):
        sf   = "anchored" if "anchor" in m or "wait" in m else ("berthed" if "berth" in m else None)
        d    = await _list_vessels(db, status=sf, limit=15); used.append("list_vessels")
        rows = "\n".join(
            f"| {v['name']} | {v['type']} | {v['status']} | {v['flag'] or '—'} |"
            for v in d["vessels"]
        )
        text = (
            f"**Vessel Fleet** — {d['count']} vessel(s)\n\n"
            f"| Name | Type | Status | Flag |\n|------|------|--------|------|\n{rows}"
        )

    elif any(w in m for w in ["allocat", "schedule", "conflict", "assignment"]):
        d    = await _allocations(db); used.append("get_port_allocations")
        rows = "\n".join(
            f"| {a['vessel']} | {a['berth']} | {a['status']} | {a['wait_min']}m | {'⚠️' if a['conflict'] else '✅'} |"
            for a in d["allocations"][:10]
        )
        text = (
            f"**Berth Allocations** — {d['count']} active, {d['conflict_count']} conflict(s)\n\n"
            f"| Vessel | Berth | Status | Wait | Flag |\n|--------|-------|--------|------|------|\n{rows}"
        )

    elif any(w in m for w in ["alert", "notif", "warning", "incident"]):
        d    = await _notifications(db); used.append("list_notifications")
        if d["count"] == 0:
            text = "No notifications on record."
        else:
            rows = "\n".join(
                f"| {n['created_at'][:16] if n['created_at'] else '—'} | {n['channel'] or '—'} | {(n['subject'] or n['body'] or '')[:50]} |"
                for n in d["notifications"][:8]
            )
            text = (
                f"**Recent Notifications** — {d['count']} record(s)\n\n"
                f"| Time | Channel | Message |\n|------|---------|--------|\n{rows}"
            )

    else:
        text = (
            "I can answer questions about live port operations. Try:\n"
            "- **\"What are the current port KPIs?\"**\n"
            "- **\"Show congestion forecast for 48 hours\"**\n"
            "- **\"Which vessels are arriving today?\"**\n"
            "- **\"Show berth status\"**\n"
            "- **\"Are there any scheduling conflicts?\"**\n"
            "- **\"Why is vessel [name] delayed?\"**"
        )

    return ChatResponse(
        response=text,
        suggested_questions=_suggestions(message),
        tool_calls_made=used,
        model_used="rule-based",
    )

# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/message", response_model=ChatResponse)
async def chat_message(
    req:          MessageRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
) -> ChatResponse:
    """Process a natural-language message and return an AI-generated port operations response."""

    api_key    = getattr(settings, "ANTHROPIC_API_KEY", "")
    model_name = getattr(settings, "CHAT_MODEL", "claude-haiku-4-5-20251001")

    if not api_key:
        return await _fallback(req.message, db)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        logger.warning("anthropic package not installed — falling back to rule-based")
        return await _fallback(req.message, db)

    # Build initial messages (keep last 10 turns to stay within context)
    messages: list[dict] = [
        {"role": m.role, "content": m.content}
        for m in req.history[-10:]
    ]
    messages.append({"role": "user", "content": req.message})

    tool_calls_made: list[str] = []

    for _iteration in range(6):  # safety loop cap
        api_resp = client.messages.create(
            model=model_name,
            max_tokens=2048,
            system=_system_prompt(),
            tools=TOOLS,
            messages=messages,
        )

        if api_resp.stop_reason == "end_turn":
            text = "".join(
                block.text
                for block in api_resp.content
                if hasattr(block, "text")
            )
            return ChatResponse(
                response=text,
                suggested_questions=_suggestions(req.message),
                tool_calls_made=tool_calls_made,
                model_used=api_resp.model,
            )

        if api_resp.stop_reason == "tool_use":
            # Serialize content blocks for the history
            asst_content = []
            tool_results  = []

            for block in api_resp.content:
                if block.type == "text":
                    asst_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    asst_content.append({
                        "type": "tool_use",
                        "id":   block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                    tool_calls_made.append(block.name)
                    result = await _dispatch(block.name, block.input or {}, db)
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     json.dumps(result, default=str),
                    })

            messages.append({"role": "assistant", "content": asst_content})
            messages.append({"role": "user",      "content": tool_results})
        else:
            break  # unexpected stop_reason

    # Extract whatever text we have from the last response
    text = "".join(
        block.text for block in api_resp.content if hasattr(block, "text")
    ) or "I was unable to complete your request. Please try again."

    return ChatResponse(
        response=text,
        suggested_questions=_suggestions(req.message),
        tool_calls_made=tool_calls_made,
        model_used=getattr(api_resp, "model", model_name),
    )


@router.get("/suggestions")
async def get_suggestions(current_user: User = Depends(get_current_user)) -> dict:
    """Return default contextual quick-start questions for the chat UI."""
    return {
        "suggestions": [
            "What are the current port KPIs?",
            "Show congestion forecast for the next 48 hours",
            "Which vessels are arriving today?",
            "What is the current berth utilization?",
            "Are there any scheduling conflicts?",
            "List vessels that are anchored or waiting",
            "Which berth has the highest utilization?",
            "Show me the most recent system alerts",
        ]
    }
