from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, require_roles
from app.models.iam import User, UserRole
from app.core.lifecycle import is_valid_vessel_transition, is_valid_visit_transition
from app.database import get_db
from app.ml.eta_predictor import eta_predictor
from app.models.berth import Berth, BerthStatus
from app.models.port import Port
from app.models.prediction import Prediction
from app.models.vessel import Vessel, VesselStatus
from app.models.visit import Visit, VisitStatus
from app.schemas.eta import (
    ETAModelInfo, PredictETAInput, PredictETAResult,
    PredictionFeedback, PredictionFeedbackResult,
)
from app.schemas.berth_ops import ETAAndBerthResult, BerthAllocationResult
from app.services.eta_service import predict_eta, _MODEL_VERSION
from app.services import berth_service

router = APIRouter()


def _parse_dt(s: str | None) -> datetime | None:
    """Safely parse an ISO datetime string to a timezone-aware datetime."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


_TERMINAL_VISIT_STATUSES = (VisitStatus.COMPLETED, VisitStatus.CANCELLED)


async def _release_berth_if_unused(
    db: AsyncSession,
    berth_id: int | None,
    exclude_visit_id: int | None = None,
) -> None:
    """
    Set a berth back to AVAILABLE if no other non-terminal visit still
    references it. Called whenever a visit moves off a berth (reassignment
    or completion) so occupancy stays in sync with the visits that actually
    justify it — a berth must never stay OCCUPIED with zero active visits.
    """
    if berth_id is None:
        return
    query = select(func.count()).select_from(Visit).where(
        Visit.berth_id == berth_id,
        Visit.status.notin_(_TERMINAL_VISIT_STATUSES),
    )
    if exclude_visit_id is not None:
        query = query.where(Visit.id != exclude_visit_id)
    still_in_use = (await db.execute(query)).scalar() or 0
    if still_in_use == 0:
        berth = await db.get(Berth, berth_id)
        if berth and berth.status == BerthStatus.OCCUPIED:
            berth.status = BerthStatus.AVAILABLE


async def _persist_allocation(
    db: AsyncSession,
    vessel_id: int,
    port_id_str: str | None,
    berth_result: BerthAllocationResult,
    eta_result: PredictETAResult,
) -> None:
    """
    Write the AI pipeline result to the database so the dashboard,
    Port Operations tab, and Berth Board all see live data.

    Actions:
      1. Look up Port and Berth rows by their string codes.
      2. Create (or update) a Visit record with status=APPROACHING.
      3. Mark the assigned Berth as OCCUPIED.
      4. Link the saved Prediction row back to the Visit.
      5. Update Vessel status to APPROACHING.
    """
    # ── 1. Resolve Port DB row ────────────────────────────────────────────────
    port_db: Port | None = None
    if port_id_str:
        res = await db.execute(select(Port).where(Port.code == port_id_str.upper()))
        port_db = res.scalar_one_or_none()

    # ── 2. Resolve Berth DB row ───────────────────────────────────────────────
    berth_db: Berth | None = None
    if berth_result.assigned_berth:
        res = await db.execute(
            select(Berth).where(Berth.code == berth_result.assigned_berth)
        )
        berth_db = res.scalar_one_or_none()

    # ── 3. Parse scheduling datetimes ─────────────────────────────────────────
    eta_dt = _parse_dt(eta_result.predicted_eta)
    etb_dt = _parse_dt(berth_result.berthing_start_time)
    etd_dt = _parse_dt(berth_result.departure_time)
    wait_h = (
        round(berth_result.waiting_time_minutes / 60.0, 3)
        if berth_result.waiting_time_minutes
        else None
    )
    berth_h = (
        round((etd_dt - etb_dt).total_seconds() / 3600, 3)
        if etd_dt and etb_dt
        else None
    )
    turnaround_h = (
        round((berth_h or 0) + (wait_h or 0), 3)
        if berth_h is not None or wait_h is not None
        else None
    )

    # ── 4. Create or update Visit ─────────────────────────────────────────────
    active_statuses = [
        VisitStatus.SCHEDULED,   VisitStatus.APPROACHING, VisitStatus.ANCHORED,
        VisitStatus.BERTHING,    VisitStatus.IN_PORT,     VisitStatus.DEPARTING,
    ]
    existing_res = await db.execute(
        select(Visit)
        .where(Visit.vessel_id == vessel_id, Visit.status.in_(active_statuses))
        .order_by(Visit.created_at.desc())
        .limit(1)
    )
    existing_visit: Visit | None = existing_res.scalar_one_or_none()

    if existing_visit:
        old_berth_id                       = existing_visit.berth_id
        new_berth_id                       = berth_db.id if berth_db else old_berth_id
        existing_visit.port_id             = port_db.id if port_db else existing_visit.port_id
        existing_visit.berth_id            = new_berth_id
        # If the AI engine moved this vessel to a different berth, the old
        # one is no longer occupied by this visit — release it (unless some
        # other active visit still legitimately holds it).
        if old_berth_id is not None and old_berth_id != new_berth_id:
            await _release_berth_if_unused(db, old_berth_id, exclude_visit_id=existing_visit.id)
        # Only advance status forward — a repeated ETA call for a vessel that
        # has already progressed (e.g. ANCHORED, IN_PORT) must not reset it
        # back to APPROACHING.
        if is_valid_visit_transition(existing_visit.status, VisitStatus.APPROACHING):
            existing_visit.status = VisitStatus.APPROACHING
        existing_visit.eta                 = eta_dt  or existing_visit.eta
        existing_visit.etb                 = etb_dt  or existing_visit.etb
        existing_visit.etd                 = etd_dt  or existing_visit.etd
        existing_visit.waiting_time_hours  = wait_h  or existing_visit.waiting_time_hours
        existing_visit.berth_time_hours    = berth_h or existing_visit.berth_time_hours
        existing_visit.turnaround_hours    = turnaround_h or existing_visit.turnaround_hours
        existing_visit.notes               = (
            f"AI berth: {berth_result.assigned_berth} | "
            f"wait {berth_result.waiting_time_minutes:.0f} min | "
            f"req {berth_result.request_id}"
        )
        visit = existing_visit
    else:
        visit = Visit(
            vessel_id          = vessel_id,
            port_id            = port_db.id  if port_db  else None,
            berth_id           = berth_db.id if berth_db else None,
            status             = VisitStatus.APPROACHING,
            eta                = eta_dt,
            etb                = etb_dt,
            etd                = etd_dt,
            waiting_time_hours = wait_h,
            berth_time_hours   = berth_h,
            turnaround_hours   = turnaround_h,
            notes              = (
                f"AI berth: {berth_result.assigned_berth} | "
                f"wait {berth_result.waiting_time_minutes:.0f} min | "
                f"req {berth_result.request_id}"
            ),
        )
        db.add(visit)
        await db.flush()     # populate visit.id before linking prediction

    # ── 5. Mark assigned Berth as OCCUPIED ────────────────────────────────────
    if berth_db and berth_db.status != BerthStatus.OCCUPIED:
        berth_db.status = BerthStatus.OCCUPIED

    # ── 6. Link the Prediction row back to this Visit ─────────────────────────
    if eta_result.prediction_id:
        pred: Prediction | None = await db.get(Prediction, eta_result.prediction_id)
        if pred and pred.visit_id is None:
            pred.visit_id = visit.id

    # ── 7. Update Vessel status to APPROACHING ────────────────────────────────
    vessel_obj: Vessel | None = await db.get(Vessel, vessel_id)
    if vessel_obj and vessel_obj.status == VesselStatus.AT_SEA:
        vessel_obj.status = VesselStatus.APPROACHING


@router.post("/predict/eta", response_model=PredictETAResult)
async def predict_vessel_eta(payload: PredictETAInput, db: AsyncSession = Depends(get_db)):
    """
    Predict vessel ETA delay using the CatBoost ML model.
    MAE ≈ 6.5 min · R² ≈ 0.82 · 38 features.
    Persists result as a Prediction record.
    """
    if eta_predictor is None:
        raise HTTPException(status_code=503, detail="ETA model not loaded.")
    try:
        return await predict_eta(payload, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")


@router.post("/predict/eta-and-berth", response_model=ETAAndBerthResult)
async def predict_eta_and_allocate_berth(
    payload: PredictETAInput,
    db: AsyncSession = Depends(get_db),
):
    """
    **Two-stage AI pipeline** — runs in a single request:

    1. **Stage 1** — CatBoost ETA model predicts delay + arrival time
    2. **Stage 2** — Berth Optimizer allocates the optimal berth using Stage 1 outputs

    Returns a unified response combining both model results.
    If Stage 2 fails (e.g. no berths), the `eta` field is still populated
    and `berth_error` describes the failure.
    """
    if eta_predictor is None:
        raise HTTPException(status_code=503, detail="ETA model not loaded.")

    # ── Stage 1: ETA prediction ────────────────────────────────────────────
    try:
        eta_result = await predict_eta(payload, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ETA prediction failed: {e}")

    # ── Stage 2: Berth allocation ──────────────────────────────────────────
    berth_result: BerthAllocationResult | None = None
    berth_error: str | None = None
    try:
        # Resolve vessel physical specs — use payload overrides, fall back to ETA service defaults
        vessel = await db.get(Vessel, payload.vessel_id)
        loa_m         = payload.loa_m         or (vessel.length_overall if vessel else 180.0) or 180.0
        draft_m       = payload.draft_m        or (vessel.max_draft if vessel else 9.0)       or 9.0
        gross_tonnage = payload.gross_tonnage  or (int(vessel.gross_tonnage) if vessel and vessel.gross_tonnage else 25_000)
        vessel_age    = payload.vessel_age_years or 10.0
        vessel_type   = payload.vessel_type    or (vessel.vessel_type.value if vessel else "container")

        allocation = berth_service.allocate_berth_for_vessel(
            vessel_id               = str(payload.vessel_id),
            predicted_eta           = eta_result.predicted_eta or payload.scheduled_eta,
            predicted_delay_minutes = eta_result.predicted_delay_minutes,
            vessel_type             = vessel_type,
            loa_m                   = float(loa_m),
            draft_m                 = float(draft_m),
            gross_tonnage           = float(gross_tonnage),
            vessel_age_years        = float(vessel_age),
            speed_knots             = payload.speed_knots,
            distance_to_port_nm     = payload.distance_to_port_nm,
            port_id                 = payload.port_id or "",
            port_congestion_index   = payload.port_congestion_index,
            traffic_density         = payload.traffic_density,
            port_avg_delay_last_24h = payload.port_avg_delay_last_24h,
            estimated_service_time_hours = payload.estimated_service_time_hours,
            wave_height_m           = payload.wave_height_m,
        )
        berth_result = BerthAllocationResult(**allocation)

        # ── Persist allocation to DB so dashboard / port-ops / berth-board ──
        # see it immediately without a server restart or manual entry.
        try:
            await _persist_allocation(
                db          = db,
                vessel_id   = payload.vessel_id,
                port_id_str = payload.port_id,
                berth_result= berth_result,
                eta_result  = eta_result,
            )
        except Exception as persist_err:
            # Non-fatal: prediction already succeeded, just log the persistence failure.
            import logging
            logging.getLogger(__name__).warning(
                "Failed to persist berth allocation to DB: %s", persist_err
            )

    except Exception as e:
        berth_error = str(e)

    return ETAAndBerthResult(
        eta         = eta_result,
        berth       = berth_result,
        berth_error = berth_error,
    )


@router.get("/model-info", response_model=ETAModelInfo)
async def get_model_info():
    """Return ETA model metadata: all model metrics, feature importance, version, and age."""
    if eta_predictor is None:
        raise HTTPException(status_code=503, detail="ETA model not loaded.")
    age = eta_predictor.model_age_days
    staleness: str | None = None
    if age > 180:
        staleness = f"Model is {age} days old — consider retraining with recent data."
    elif age > 90:
        staleness = f"Model is {age} days old — retraining recommended soon."
    return ETAModelInfo(
        model_name         = eta_predictor.model_name,
        model_version      = _MODEL_VERSION,
        saved_at           = eta_predictor.saved_at,
        model_age_days     = age,
        staleness_warning  = staleness,
        metrics            = eta_predictor.metrics,
        feature_count      = len(eta_predictor.feature_names),
        feature_importance = eta_predictor.get_feature_importance(top_n=20),
        status             = "loaded",
        available_models   = eta_predictor.available_models,
    )


@router.post("/set-active-model")
async def set_active_model(
    payload: dict,
    _user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.PORT_MANAGER))],
):
    """Switch the active prediction model at runtime without retraining."""
    if eta_predictor is None:
        raise HTTPException(status_code=503, detail="ETA model not loaded.")
    name = payload.get("model_name", "")
    if not name:
        raise HTTPException(status_code=400, detail="model_name is required.")
    try:
        eta_predictor.set_active_model(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "active_model":      eta_predictor.model_name,
        "available_models":  eta_predictor.available_models,
        "metrics":           eta_predictor.metrics.get(eta_predictor.model_name, {}),
        "status": "ok",
    }


@router.post("/predict/feedback", response_model=PredictionFeedbackResult)
async def record_prediction_feedback(
    payload: PredictionFeedback,
    _user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Record the actual arrival delay for a past ETA prediction.

    Updates the Prediction row with `actual_value`, `actual_datetime`, and
    `error_mae` so model accuracy can be tracked over time.
    Any authenticated user can submit feedback (e.g. vessel agents at arrival).
    """
    pred: Prediction | None = await db.get(Prediction, payload.prediction_id)
    if pred is None:
        raise HTTPException(status_code=404, detail=f"Prediction {payload.prediction_id} not found.")

    pred.actual_value = payload.actual_delay_minutes
    if payload.actual_arrival_time:
        try:
            pred.actual_datetime = datetime.fromisoformat(
                payload.actual_arrival_time.replace("Z", "+00:00")
            )
        except ValueError:
            raise HTTPException(status_code=422, detail="actual_arrival_time must be ISO-8601.")

    error = abs((pred.predicted_value or 0.0) - payload.actual_delay_minutes)
    pred.error_mae = round(error, 2)

    await db.commit()

    return PredictionFeedbackResult(
        prediction_id     = pred.id,
        predicted_minutes = round(pred.predicted_value or 0.0, 1),
        actual_minutes    = payload.actual_delay_minutes,
        error_minutes     = pred.error_mae,
        message           = (
            f"Feedback recorded. Prediction error: {pred.error_mae:.1f} min "
            f"({'under' if pred.predicted_value < payload.actual_delay_minutes else 'over'}estimated)."
        ),
    )


@router.get("/evaluation")
async def get_model_evaluation(
    _user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.PORT_MANAGER, UserRole.ANALYST))],
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregate ETA prediction accuracy across all stored predictions that
    have ground-truth actual values.  Returns overall stats, breakdown by
    vessel type and port, and the model's global feature importance.
    """
    # ── Overall stats ─────────────────────────────────────────────────────────
    overall_row = (await db.execute(text("""
        WITH base AS (
            SELECT actual_value, predicted_value, error_mae
            FROM   predictions
            WHERE  status = 'COMPLETED' AND actual_value IS NOT NULL
        ),
        mean_cte AS (SELECT AVG(actual_value) AS mean_actual FROM base)
        SELECT
            COUNT(*)                                                   AS n,
            AVG(error_mae)                                             AS mae,
            SQRT(AVG(error_mae * error_mae))                           AS rmse,
            1 - SUM((actual_value - predicted_value)^2)
                / NULLIF(SUM((actual_value - mean_cte.mean_actual)^2), 0) AS r2,
            AVG(predicted_value - actual_value)                        AS bias,
            100.0 * COUNT(*) FILTER (WHERE error_mae <= 15) / COUNT(*) AS within_15_pct,
            100.0 * COUNT(*) FILTER (WHERE error_mae <= 30) / COUNT(*) AS within_30_pct,
            MIN(actual_value)                                          AS min_actual,
            MAX(actual_value)                                          AS max_actual,
            mean_cte.mean_actual
        FROM base, mean_cte
        GROUP BY mean_cte.mean_actual
    """))).mappings().first()

    if not overall_row or not overall_row["n"]:
        raise HTTPException(404, "No evaluated predictions found. Import data first.")

    # ── By vessel type ────────────────────────────────────────────────────────
    by_type_rows = (await db.execute(text("""
        SELECT
            v.vessel_type,
            COUNT(*)         AS n,
            AVG(p.error_mae) AS mae,
            SQRT(AVG(p.error_mae * p.error_mae)) AS rmse
        FROM predictions p
        JOIN vessels v ON v.id = p.vessel_id
        WHERE p.status = 'COMPLETED' AND p.actual_value IS NOT NULL
        GROUP BY v.vessel_type
        ORDER BY mae
    """))).mappings().all()

    # ── By port ───────────────────────────────────────────────────────────────
    by_port_rows = (await db.execute(text("""
        SELECT
            po.code              AS port_code,
            COUNT(*)             AS n,
            AVG(p.error_mae)     AS mae,
            SQRT(AVG(p.error_mae * p.error_mae)) AS rmse
        FROM predictions p
        JOIN visits vi ON vi.id = p.visit_id
        JOIN ports  po ON po.id = vi.port_id
        WHERE p.status = 'COMPLETED' AND p.actual_value IS NOT NULL
        GROUP BY po.code
        ORDER BY po.code
    """))).mappings().all()

    # ── Sample of predicted vs actual for scatter chart (up to 500 pts) ──────
    sample_rows = (await db.execute(text("""
        SELECT actual_value, predicted_value
        FROM   predictions
        WHERE  status = 'COMPLETED' AND actual_value IS NOT NULL
        ORDER  BY RANDOM()
        LIMIT  500
    """))).mappings().all()

    # ── Feature importance from loaded model ─────────────────────────────────
    fi = eta_predictor.get_feature_importance(top_n=15) if eta_predictor else []

    return {
        "summary": {
            "n":             int(overall_row["n"]),
            "mae":           round(float(overall_row["mae"]),  2),
            "rmse":          round(float(overall_row["rmse"]), 2),
            "r2":            round(float(overall_row["r2"]),   4),
            "bias":          round(float(overall_row["bias"]), 2),
            "within_15_pct": round(float(overall_row["within_15_pct"]), 1),
            "within_30_pct": round(float(overall_row["within_30_pct"]), 1),
            "min_actual":    round(float(overall_row["min_actual"]), 1),
            "max_actual":    round(float(overall_row["max_actual"]), 1),
            "mean_actual":   round(float(overall_row["mean_actual"]), 1),
            "model_name":    eta_predictor.model_name if eta_predictor else "unknown",
            "model_mae_train": eta_predictor.mae      if eta_predictor else None,
            "model_r2_train":  eta_predictor.r2       if eta_predictor else None,
        },
        "by_vessel_type": [
            {
                "vessel_type": r["vessel_type"],
                "n":           int(r["n"]),
                "mae":         round(float(r["mae"]),  2),
                "rmse":        round(float(r["rmse"]), 2),
            }
            for r in by_type_rows
        ],
        "by_port": [
            {
                "port_code": r["port_code"],
                "n":         int(r["n"]),
                "mae":       round(float(r["mae"]),  2),
                "rmse":      round(float(r["rmse"]), 2),
            }
            for r in by_port_rows
        ],
        "scatter_sample": [
            {"actual": round(float(r["actual_value"]), 1),
             "predicted": round(float(r["predicted_value"]), 1)}
            for r in sample_rows
        ],
        "feature_importance": fi,
    }
