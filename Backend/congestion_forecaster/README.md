# Smart Port — Congestion Forecaster (Stage 3)

Stage 3 of the Smart Port AI Pipeline — architectural mirror of Stage 2's
`berth_optimizer/` package, so the three stages (ETA Prediction, Berth
Optimization, Congestion Forecast) follow the same structure.

This package was introduced in a structural refactor (Phase 3): the
prediction logic previously lived only inline at
`Backend/app/ml/congestion_predictor.py`. That file now re-exports
everything from here for backward compatibility — no prediction logic,
feature engineering, or model behavior changed, and the trained model
artifact was not moved or retrained. It still lives at
`Backend/app/ml/models/congestion_model.pkl`.

## Folder structure

```
congestion_forecaster/             ← project root / run commands from here
├── conftest.py
├── requirements.txt
├── README.md
├── engine/
│   └── predictor.py                ← CongestionPredictor (LightGBM + CatBoost)
├── api/
│   └── main.py                     ← standalone FastAPI app
├── dashboard/
│   └── app.py                      ← Streamlit dashboard
└── tests/
    └── test_predictor.py
```

## How to run (all commands from inside congestion_forecaster/)

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/test_predictor.py -v

# Start standalone API  →  http://127.0.0.1:8001/docs
uvicorn api.main:app --reload --port 8001

# Start dashboard
streamlit run dashboard/app.py
```

## Within the main app

The live FastAPI backend does not call this package's standalone `api/main.py`
— it imports the engine directly:

```python
from app.ml.congestion_predictor import congestion_predictor  # re-export, unchanged
# or, equivalently, the new canonical import:
from congestion_forecaster.engine.predictor import congestion_predictor
```

`Backend/app/api/v1/endpoints/congestion.py` and `chat.py` use the first
form (no changes needed to those files for this refactor to be safe).

## Models

| Target | Model | Metric |
|---|---|---|
| `congestion_level_future` | LightGBM | MAE 0.038, R² 93.7% |
| `queue_length_future` | CatBoost | MAE 1.69 vessels |
