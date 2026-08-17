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
