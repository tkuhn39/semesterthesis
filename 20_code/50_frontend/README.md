# 50_frontend — Next.js workbench

The workbench UI (ADR-020): FVA-Workbench layout language, modernised — model tree on the
left (Getriebe → Stufe → Ritzel/Rad → Berechnungen), condensed attribute-table editors in the
centre, dark three.js viewports for the FE mesh and the gear pair (co-moving DOF triads),
messages strip at the bottom. Geist font, Tailwind v4, DE/EN language switch (i18n keys in
`src/lib/i18n.tsx`).

## Panels

| Tree node | Panel | Backend |
|---|---|---|
| Übersicht | kst-E summary + entry tiles | `/api/example/kst-e` |
| Auslegung | presets / `.ste` import / free parameters, tool profile (DIN 3972), micro-geometry (ISO 21771 §6), tolerances | `/api/presets`, `/api/import/ste`, `/api/tolerances` |
| Geometrie | macro geometry editor | `/api/geometry` |
| Tragfähigkeit | ISO 6336 + VDI 2736 incl. static peak load | `/api/capacity` |
| Dynamikfaktoren | native K_v/K_Hα/K_Hβ + resonance | `/api/dynamics` |
| Stufenvariation | sweep, Pareto, parallel coordinates, material matrix, real-contour variant overlay | `/api/variation`, `/api/mesh/contour` |
| Zahnform (je Rad) | as-cut contour, fillet strategies incl. clearance | `/api/mesh/contour` |
| FE-Mesh (je Rad) | density presets, 3D hull + Jacobian heatmap, convergence quick check, fillet ranking/sweep | `/api/mesh/*` |
| Paar & FE-Abwälzmodell | both gears, DOF triads, roll slider, deck download (rigid-shell rule) | `/api/mesh/3d`, `/api/mesh/deck` |

## Development

```bash
npm install
npm run dev        # http://localhost:3000
```

Dev against a separately running backend needs in the shared `20_code/.env`:
`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` and `CORS_ORIGINS=http://localhost:3000`.

## Production

`npm run build` produces a static export in `out/` (no server runtime, ADR-006): FastAPI
serves it same-origin from `40_backend/app/static` — the Docker build does this copy.
The stage state (Auslegung) lives client-side; every request is stateless against the API.
