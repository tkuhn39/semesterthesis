# `30_docker` — Containerized deployment

The application ships as a **single hardened image**: a multi-stage build compiles
the React frontend and serves it together with the FastAPI backend via `uvicorn`
(ADR-006, single-image default).

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Hardened 3-stage build (Node SPA → Python venv → slim runtime). |
| `docker-compose.yml` | Build & run locally with the security options applied. |
| `../.dockerignore` | Lives at the build-context root (`20_code/`). |

## Build & run

All commands run from `20_code/` (the build context):

```bash
# compose (applies the hardening: non-root, read-only rootfs, cap-drop, …)
docker compose -f 30_docker/docker-compose.yml up --build

# or plain docker
docker build -f 30_docker/Dockerfile -t semesterthesis:latest .
docker run --rm -p 8000:8000 --env-file .env \
  -e CACHE_DIR=/data/cache -e LOG_DIR=/data/logs -e STORAGE_LOCAL_BASE_PATH=/data/output \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:size=64m --mount type=volume,src=app-data,dst=/data \
  semesterthesis:latest
```

Then open <http://localhost:8000> — the SPA is at `/`, the API under `/api/*`
(`/api/health`, OpenAPI docs at `/docs`).

## Hardening

- **Non-root**: runs as UID/GID `10001` (`USER 10001:10001`); the port is 8000 (>1024).
- **No build tools at runtime**: deps come from an isolated builder venv (`/opt/venv`);
  the final layer has no `pip`-installed compilers, the SPA `node_modules` never ship.
- **Reproducible deps**: `npm ci` (lockfile) + pinned `requirements.txt`. For strict
  supply-chain, pin the base images by digest (`FROM …@sha256:…`).
- **Read-only root filesystem**: all writable state is confined to **`/data`** (a named
  volume) — overridden via `CACHE_DIR` / `LOG_DIR` / `STORAGE_LOCAL_BASE_PATH`. `/tmp`
  is a small `tmpfs`. `HOME=/tmp`, `MPLCONFIGDIR=/tmp/mpl`.
- **Reduced kernel surface**: `cap_drop: ALL`, `security_opt: no-new-privileges`.
- **Liveness**: `HEALTHCHECK` hits `/api/health` (pure-Python, no extra packages).
- **Graceful shutdown**: `uvicorn` is PID 1 (exec form) and receives `SIGTERM`.
- **Resource limits**: 2 CPU / 1 GiB (compose `deploy.resources.limits`).

## Notes

- The SPA is served **same-origin** → no CORS / `VITE_API_BASE_URL` baked into the
  build; runtime config is injected via `env_file` / `-e`. (Keep `.env` out of the
  image — it is in `.dockerignore`.)
- Behind a reverse proxy / orchestrator, terminate TLS there; the container speaks
  plain HTTP on 8000. The read-only + non-root + cap-drop posture suits Kubernetes
  `securityContext` (`runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`).
