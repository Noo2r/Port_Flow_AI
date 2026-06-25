"""
ETA prediction service — uses the trained CatBoost ML model.
MAE ≈ 6.5 min · RMSE ≈ 8.1 min · R² ≈ 0.82
"""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.eta_predictor import eta_predictor, VESSEL_TYPE_MAP
from app.models.prediction import Prediction, PredictionStatus, PredictionType
from app.models.vessel import Vessel
from app.schemas.eta import PredictETAInput, PredictETAResult

_MODEL_VERSION = "2.0.0-catboost"


def _build_model_input(payload: PredictETAInput, vessel: Vessel) -> dict:
    """Merge request + DB vessel data into the dict ETAPredictor.predict() expects."""
    return {
        # Vessel characteristics — request overrides DB
        "vessel_type":    payload.vessel_type  or VESSEL_TYPE_MAP.get(vessel.vessel_type.value, "Container"),
        "loa_m":          payload.loa_m        or (vessel.length_overall or 180.0),
        "draft_m":        payload.draft_m      or (vessel.max_draft or 9.0),
        "gross_tonnage":  payload.gross_tonnage or (int(vessel.gross_tonnage) if vessel.gross_tonnage else 25_000),
        "engine_power_kw":payload.engine_power_kw or 30_000,
        "vessel_age_years":payload.vessel_age_years or 10.0,
        "estimated_service_time_hours": payload.estimated_service_time_hours,

        # Navigation
        "latitude":            payload.latitude,
        "longitude":           payload.longitude,
        "speed_knots":         payload.speed_knots,
        "heading":             payload.heading,
        "distance_to_port_nm": payload.distance_to_port_nm,

        # Port conditions
        "port_id":                  payload.port_id,
        "traffic_density":          payload.traffic_density,
        "berth_max_length":         payload.berth_max_length,
        "berth_queue_length":       payload.berth_queue_length,
        "crane_availability_ratio": payload.crane_availability_ratio,
        "port_congestion_index":    payload.port_congestion_index,
        "port_avg_delay_last_24h":  payload.port_avg_delay_last_24h,

        # Weather
        "wave_height_m":    payload.wave_height_m,
        "wind_speed_knots": payload.wind_speed_knots,
        "visibility_km":    payload.visibility_km,
        "precipitation_mm": payload.precipitation_mm,
        "temperature_c":    payload.temperature_c,

        # Scheduling
        "timestamp":            payload.timestamp,
        "scheduled_eta":        payload.scheduled_eta,
        "berth_available_from": payload.berth_available_from or payload.timestamp,
    }


async def predict_eta(payload: PredictETAInput, db: AsyncSession) -> PredictETAResult:
    # Fetch vessel
    vessel = await db.get(Vessel, payload.vessel_id)
    if vessel is None:
        raise ValueError(f"Vessel {payload.vessel_id} not found")

    # Run ML model
    model_input = _build_model_input(payload, vessel)
    result = eta_predictor.predict(model_input)

    # Parse predicted datetime for DB storage
    pred_dt: datetime | None = None
    if result["predicted_eta"]:
        try:
            pred_dt = datetime.fromisoformat(
                result["predicted_eta"].replace("Z", "+00:00")
            )
        except Exception:
            pass

    # Persist prediction record
    prediction = Prediction(
        vessel_id        = payload.vessel_id,
        visit_id         = payload.visit_id,
        prediction_type  = PredictionType.ETA,
        status           = PredictionStatus.COMPLETED,
        model_name       = result["model_used"],
        model_version    = _MODEL_VERSION,
        predicted_value  = result["predicted_delay_minutes"],
        predicted_datetime = pred_dt,
        confidence_score = result["confidence_score"],
        lower_bound      = result["lower_bound_minutes"],
        upper_bound      = result["upper_bound_minutes"],
        input_features   = {k: v for k, v in model_input.items()
                            if not isinstance(v, (bytes, bytearray))},
    )
    db.add(prediction)
    await db.flush()

    return PredictETAResult(
        vessel_id               = payload.vessel_id,
        visit_id                = payload.visit_id,
        model_name              = result["model_used"],
        model_version           = _MODEL_VERSION,
        predicted_delay_minutes = result["predicted_delay_minutes"],
        predicted_eta           = result["predicted_eta"],
        confidence_score        = result["confidence_score"],
        lower_bound_minutes     = result["lower_bound_minutes"],
        upper_bound_minutes     = result["upper_bound_minutes"],
        top_delay_factors       = result["top_factors"],
        model_mae_minutes       = eta_predictor.mae,
        model_r2                = eta_predictor.r2,
        model_age_days          = result.get("model_age_days"),
        staleness_warning       = result.get("staleness_warning"),
        prediction_id           = prediction.id,
        created_at              = prediction.created_at.isoformat(),
    )
