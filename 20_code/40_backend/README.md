# `40_backend` — FastAPI application

REST API for the plastic-gear tooth root stress tool.

## Layout

```
40_backend/
├── app/
│   ├── __init__.py        # version
│   ├── config.py          # typed settings from .env (pydantic-settings)
│   ├── main.py            # ASGI app factory, CORS, static SPA mount
│   └── api/
│       └── routes.py      # /api/* endpoints
└── tests/
    └── test_health.py
```

## Run (development)

```bash
conda activate semesterthesis_3-12
cd 20_code/40_backend
uvicorn app.main:app --reload --port 8000
```

- API docs: <http://localhost:8000/docs>
- Health:   <http://localhost:8000/api/health>

Configuration is read from `20_code/.env` (see `.env.example`).

## Test

```bash
cd 20_code && pytest 40_backend
```
