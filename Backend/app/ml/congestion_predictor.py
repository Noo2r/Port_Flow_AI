"""
Congestion Forecaster — compatibility re-export
=================================================
The real implementation now lives in the standalone
`congestion_forecaster/engine/predictor.py` package (Backend/congestion_forecaster/),
mirroring the architecture of Stage 2's `berth_optimizer/` package — its own
engine, FastAPI app, Streamlit dashboard, and pytest suite. This module is
kept as a thin re-export so existing imports
(`from app.ml.congestion_predictor import congestion_predictor`) continue to
work unchanged. No prediction logic, model behavior, or model artifact
changed — this is a structural refactor only.

Usage (unchanged)
------------------
    from app.ml.congestion_predictor import congestion_predictor
    result = congestion_predictor.predict(input_dict)
"""

from congestion_forecaster.engine.predictor import (  # noqa: F401
    CongestionPredictor,
    VESSEL_TYPE_MAP,
    TRAFFIC_MAP,
    congestion_predictor,
)
