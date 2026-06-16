# `30_docker` — Containerized deployment

The application ships as a **single image**: a multi-stage build compiles the
React frontend and then serves it together with the FastAPI backend via
`uvicorn`.

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build (Node → Python runtime). |
| `docker-compose.yml` | Convenience wrapper to build & run locally. |
| `../.dockerignore` | Lives at the build-context root (`20_code/`). |

## Build & run

All commands are run from `20_code/` (the build context):

```bash
# with compose
docker compose -f 30_docker/docker-compose.yml up --build

# or plain docker
docker build -f 30_docker/Dockerfile -t semesterthesis:latest .
docker run --rm -p 8000:8000 --env-file .env semesterthesis:latest
```

Then open <http://localhost:8000> — the SPA is served at `/` and the API under
`/api/*` (docs at `/docs`).

## Notes

- The SPA is served same-origin by the backend, so no CORS configuration is
  needed in the container.
- Runtime configuration is injected via `--env-file .env` / compose `env_file`.
