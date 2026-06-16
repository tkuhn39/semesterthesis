# `50_frontend` — React (Vite) SPA

Single-page app for the plastic-gear tooth root stress tool.

## Stack

- React 19
- Vite 6 (dev server on port `5173`)

## Develop

```bash
cd 20_code/50_frontend
npm install
npm run dev
```

The app reads `VITE_API_BASE_URL` from the shared `20_code/.env`
(Vite `envDir` points one level up), so a single `.env` configures both
backend and frontend.

## Build

```bash
npm run build      # outputs to dist/
npm run preview    # serve the production build locally
```

In the Docker image the contents of `dist/` are copied into the backend and
served by FastAPI as static files (see `../30_docker/`).
