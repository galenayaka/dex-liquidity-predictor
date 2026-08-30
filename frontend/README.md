# DEX Liquidity Predictor — Frontend

Next.js (App Router) + Tailwind CSS dashboard that consumes the FastAPI
backend's real-time WebSocket stream (`/ws`).

## Structure

- `app/page.tsx` — dashboard page (sidebar + main content area).
- `app/layout.tsx`, `app/globals.css` — root layout & Tailwind setup.
- `components/Sidebar.tsx` — navigation sidebar with connection status.
- `components/AlertBanner.tsx` — red banner on `risk_level: "High"` events.
- `components/PricePanel.tsx` — live pool price table.
- `components/PredictionPanel.tsx` — liquidity-drain predictions & alerts.
- `hooks/useWebSocket.ts` — WebSocket hook with auto-reconnect.
- `lib/types.ts` — types mirroring the backend Pydantic schemas.

## Getting started

1. Start the backend first (see `backend/README.md`), e.g.:

   ```bash
   cd ../backend && python -m uvicorn app.main:app --reload --port 8000
   ```

2. Install dependencies and run the dev server:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. Open http://localhost:3000.

## Configuration

Copy `.env.example` to `.env.local` to override the WebSocket endpoint:

```bash
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## WebSocket message shapes consumed

| `type`     | Source           | Used for                                  |
| ---------- | ---------------- | ----------------------------------------- |
| `snapshot` | on connect       | pool price table                          |
| `event`    | Swap/Burn stream | prediction + `risk_level` alert banner    |
| `alert`    | monitor loop     | HIGH / CRITICAL warning banner            |

## Deployment (static export)

The frontend uses `output: "export"`, so `npm run build` produces a fully static
site in `frontend/out/` — no Node server is required in production.

```bash
cd frontend
npm run build          # -> frontend/out/
```

Serve `out/` from any static host, or copy it into the Laravel `public/` folder
so Apache serves it next to the API:

```powershell
# from the repo root
Remove-Item -Recurse -Force public\_next -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force frontend\out\* public\
```

### Asset base path

By default the build assumes the site is served from the **domain root**, so
CSS/JS URLs are written as `/_next/...`. If you host the dashboard under a
sub-folder, set the base path when building:

```bash
NEXT_PUBLIC_BASE_PATH=/my-dashboard NEXT_PUBLIC_ASSET_PREFIX=/my-dashboard npm run build
```

> Do **not** hardcode a machine-local path (e.g. `/dex-liquidity-predictor/public`)
> in `next.config.mjs` — it bakes an absolute URL into every CSS/JS asset and
> breaks the UI on any other host.

### Backend URLs

The WebSocket/API/forecast endpoints are baked in at build time from the
`NEXT_PUBLIC_*` env vars. Set them to your production hosts before building:

```bash
NEXT_PUBLIC_WS_URL=wss://api.example.com/ws \
NEXT_PUBLIC_API_URL=https://api.example.com \
NEXT_PUBLIC_FORECAST_URL=https://forecast.example.com \
npm run build
```

