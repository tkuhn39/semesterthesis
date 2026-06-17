# `50_frontend` — React (Vite + TypeScript) SPA

The web UI for the gear-analysis tool. **Anthropic/Claude layout language with the
TUM 2022 web colour palette** (see memory `ui-design-tokens`): editorial whitespace,
a serif display face (Fraunces), TUM-blue accents, calm rounded cards.

## Stack

- React 19 · Vite 6 · TypeScript (strict)
- No UI framework — a small **own CSS design system** (`src/index.css`, tokens as CSS
  custom properties). Fonts via Google Fonts `<link>` (Fraunces / Inter / JetBrains Mono).

## Structure

```
src/
  index.css          design tokens (TUM palette) + component styles
  lib/api.ts         typed client for the FastAPI backend
  lib/format.ts      number formatting + safety classification
  components/        Layout (sidebar/topbar), ui.tsx (Card/Field/Stat/Badge/Tabs…), icons
  views/             Overview · Geometry · Capacity · Dynamics · Stufenvariation
  App.tsx            shell + view routing (state-based, no router dep)
```

The backend (`40_backend/app/api/analysis.py`) preloads the validated **kst-E**
steel–plastic pair; each view edits operating parameters and recomputes live (steel →
ISO 6336, plastic → VDI 2736). Extension points: a standard-gear example library and
STplus/RIKOR import.

## Develop

```bash
cd 20_code/40_backend && uvicorn app.main:app --reload   # API on :8000
cd 20_code/50_frontend && npm install && npm run dev      # SPA on :5173
```

`VITE_API_BASE_URL` (and `CORS_ORIGINS`) come from the shared `20_code/.env`
(Vite `envDir` points one level up), so one `.env` configures both ends.

## Build & checks

```bash
npm run typecheck   # tsc --noEmit (strict)
npm run build       # → dist/ (copied into the backend image, served by FastAPI)
npm run preview
```
