# PortFlow AI — Smart Port Operations System

Full-stack AI-powered port management system with ETA prediction, berth optimization, and congestion forecasting.

## Quick Start

### Windows
```
Double-click setup.bat
```
Or from Command Prompt:
```cmd
setup.bat
```

### Linux / macOS
```bash
chmod +x setup.sh
./setup.sh
```

That's it. The script will build and start everything automatically.

---

## What runs

| Service  | URL                        | Description                   |
|----------|----------------------------|-------------------------------|
| Frontend | http://localhost:5173      | React dashboard (nginx)       |
| Backend  | http://localhost:8000      | FastAPI REST API              |
| API Docs | http://localhost:8000/docs | Swagger UI                    |

## Login credentials
- **Email:** admin@portflow.ai
- **Password:** Admin1234!

## Requirements
- **Docker Desktop** (Windows/Mac): https://www.docker.com/products/docker-desktop
- **Docker Engine** (Linux): https://docs.docker.com/engine/install/
- ~4 GB free disk space (images + database)
- ~2 GB RAM

## First-run time
Building from source takes ~5-8 minutes on first run. Subsequent starts take ~30 seconds.

## Common commands
```bash
# Start
docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f

# View only API logs
docker compose logs -f api

# Restart a service
docker compose restart api

# Full reset (WARNING: deletes all data)
docker compose down -v
```

## Testing

**Never run `pytest` against the demo stack.** `Backend/tests/conftest.py`'s
integration tests (the `client`/`auth_client` fixtures) create and modify
real database rows — vessels, visits, ports, users. Running them against
the demo API (port 8000 / demo DB on port 5432) pollutes the exact data your
Dashboard, Analytics, and Port Operations pages display.

Instead, there's a completely separate, isolated test stack
(`docker-compose.test.yml`) — different container names, different host
ports (test API: 8001, test DB: 5433, test Redis: 6380), different database
name, ephemeral storage. It is structurally impossible for it to touch the
demo database, because it *is* a different database server.

### Run tests safely

```bash
# 1. Start the isolated test stack (builds on first run, ~1 min)
docker compose -f docker-compose.test.yml up -d --build

# 2. Run the full suite against it
docker exec -e TEST_API_BASE_URL=http://localhost:8000 portflow_test_api \
  python -m pytest tests/ congestion_forecaster/tests/ berth_optimizer/tests/ -v

# 3. Tear it down (storage is ephemeral — this fully wipes test data, no
#    separate "reset" step needed)
docker compose -f docker-compose.test.yml down -v
```

Why the `TEST_API_BASE_URL=http://localhost:8000` override in step 2: from
*outside* Docker, the test API is reachable at `localhost:8001` (the host
port mapping) — that's `conftest.py`'s default, so running `pytest` directly
from a host Python environment needs no override at all. But step 2 above
runs pytest *inside* the `portflow_test_api` container itself (so it doesn't
need pytest installed on your host) — from inside that container, its own
service listens on port 8000, not 8001 (8001 only exists as a host-side
mapping). If you have a local Python environment with the Backend
dependencies installed, you can skip the override entirely and just run
`pytest` from the `Backend/` directory on your host machine.

Unit tests (the majority of the suite — anything using `unit_client` or
`auth_unit_client`) never touch any real database at all, mocked or
isolated; they run safely with no test stack running, e.g.:
```bash
docker exec portflow_test_api python -m pytest tests/test_lifecycle.py -v
```
If the isolated test stack isn't running, `pytest` automatically skips
integration-marked tests with a clear message instead of failing with a
confusing connection error — unit tests still run normally.

### Reset the test database
Test data is stored on `tmpfs` (RAM, not disk) — there is no persistent
volume to clean up. `docker compose -f docker-compose.test.yml down -v`
(or even a plain `down`) discards all test data immediately; the next
`up` starts from an empty schema (migrations re-run, one default admin
user gets seeded by `app/db/seed.py`, nothing else).

### Reset the demo database
This is the **production/demo** data — only do this if you actually want
to wipe and re-restore from the original 12,000-vessel backup:
```bash
docker compose down -v        # deletes the demo Postgres volume
docker compose up -d --build  # re-restores from data/portflow_backup.sql
```

## Project structure
```
PortFlowAI/
├── Backend/          FastAPI Python backend
│   ├── app/          Application code
│   │   ├── api/      REST endpoints
│   │   ├── ml/       ML model wrappers + model files (.pkl)
│   │   ├── models/   SQLAlchemy ORM models
│   │   └── schemas/  Pydantic schemas
│   ├── scripts/      Training / seeding scripts
│   ├── Dockerfile
│   └── requirements.txt
├── Frontend/         React + Vite + Tailwind CSS
│   ├── src/
│   │   ├── pages/    Dashboard pages
│   │   ├── components/
│   │   └── services/ API client
│   ├── Dockerfile
│   └── nginx.conf
├── data/
│   ├── portflow_backup.sql   Full database dump (12,000 vessels + predictions)
│   └── port_flow_dataset.csv Training dataset (12,000 rows)
├── docker-compose.yml
├── setup.bat         Windows one-click setup
├── setup.sh          Linux/macOS one-click setup
└── README.md
```

## Dataset Provenance
`data/port_flow_dataset.csv` is produced entirely by the custom simulator at
`Backend/scripts/smart_port_generator.py` (physics-inspired speed/weather/queueing
formulas, seeded with `RANDOM_SEED = 42` for reproducibility). It is not scraped,
downloaded, or LLM-generated. Re-running the script reproduces the exact 12,000-row,
42-column dataset shipped with this repo.

## AI Pipeline
| Stage | Model | Metric |
|-------|-------|--------|
| ETA Prediction | CatBoost | MAE 6.28 min, R² 82.7% |
| Berth Optimization | Rule-based engine | 96 berths |
| Congestion Forecast | LightGBM + CatBoost | MAE 0.038, R² 93.7% |

## Retrain models (optional)
```bash
# Retrain ETA model (all 3 candidate models)
docker exec portflow_api python scripts/fast_compare.py

# Retrain congestion model
docker exec portflow_api python scripts/train_congestion.py

# Regenerate the Digital Twin datasets (optional — already shipped in Backend/data_digital_twin/)
docker exec portflow_api python scripts/digital_twin_generator.py

# Re-import the Digital Twin datasets into the database
docker exec portflow_api python scripts/import_digital_twin.py
```
All scripts live at `/app/scripts/` inside the container (set by `WORKDIR /app` +
`COPY . .` in `Backend/Dockerfile`), so paths are relative to `/app` — not `/tmp/`.

## Architecture Notes

### Two docker-compose files — which one to use
- **`docker-compose.yml` (root)** — the full demo stack: db + redis + api +
  frontend, with the database auto-restored from `data/portflow_backup.sql`
  (12,000 vessels, seeded admin user). `Start.bat`, `setup.bat`, and `setup.sh`
  all use this one. **Use this for demos and normal local development.**
- **`Backend/docker-compose.yml`** — a backend-only dev stack (db + redis + api,
  no frontend, no DB restore/seed). Useful for testing backend changes in
  isolation against a clean schema. Starts with an **empty** database — you'll
  need to seed it yourself (`docker exec portflow_api python scripts/import_digital_twin.py`,
  after first generating the CSVs with `scripts/digital_twin_generator.py` if
  `Backend/data_digital_twin/` doesn't already exist) before there's any data to query.

Both files now carry a header comment pointing here, so picking the wrong one
for the wrong purpose is one read away from being obvious.

### Two berth-optimizer implementations — both are real, not duplicates
- **`Backend/berth_optimizer/engine/optimizer.py`** (`BerthOptimizationEngine`)
  is the actual **Stage 2 AI model** described in the project's 3-stage
  pipeline: per-vessel constraint validation (LOA/draft fit), scoring-based
  berth selection, conflict detection, and utilization tracking. It ships
  with its own FastAPI app, Streamlit dashboard, and pytest suite under
  `Backend/berth_optimizer/`. It's wired into the live system as a singleton
  via `Backend/app/services/berth_service.py`, which the real-time
  ETA-prediction flow (`Backend/app/api/v1/endpoints/eta.py`) calls to assign
  a berth to a single arriving vessel at the moment its ETA is predicted.
- **`Backend/app/services/berth_optimizer.py`** (`optimize_berth_assignments`)
  is a much simpler **greedy batch utility**: it sweeps all currently
  `SCHEDULED`-but-unassigned visits and fills open berths first-come,
  first-served by priority, with only a basic time-overlap check — no LOA/draft
  validation, no scoring. It's called from one place only:
  `POST /api/v1/opt/optimize` (`Backend/app/api/v1/endpoints/optimization.py`),
  an admin/ops "catch-up" sweep for visits the real-time flow never got to
  assign a berth to.

**Recommendation:** keep both — they answer different questions (real-time
single-vessel AI allocation vs. batch catch-up sweep) — but the shared name
"berth optimizer" for two different things is a genuine Q&A risk. Consider
renaming `app/services/berth_optimizer.py` to `app/services/berth_batch_sweep.py`
in a future pass to make the split self-evident from the filename alone.
