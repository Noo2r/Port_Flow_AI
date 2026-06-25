# Smart Port — Berth Optimization System (v2)

Stage 2 of the Smart Port AI Pipeline.

## Folder structure

```
berth_optimizer/               ← project root / run commands from here
├── port_flow_dataset.csv      ← put CSV here  ✓
├── conftest.py
├── requirements.txt
├── README.md
├── engine/
│   └── optimizer.py
├── api/
│   └── main.py
├── dashboard/
│   └── app.py
├── utils/
│   └── data_loader.py
├── examples/
│   └── integration_demo.py
└── tests/
    └── test_optimizer.py
```

## How to run (all commands from inside berth_optimizer/)

```bash
# Install dependencies
pip install -r requirements.txt

# Run demo
python examples/integration_demo.py

# Run tests
pytest tests/test_optimizer.py -v

# Start API  →  http://127.0.0.1:8000/docs
uvicorn api.main:app --reload --port 8000

# Start dashboard
streamlit run dashboard/app.py
```

## Notes
- Place port_flow_dataset.csv inside berth_optimizer/ (same folder as this README).
- All commands are run from inside the berth_optimizer/ folder.
