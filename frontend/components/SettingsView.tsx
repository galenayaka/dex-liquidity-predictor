"use client";

import type { ReactNode } from "react";
import type { ConnectionStatus } from "@/hooks/useWebSocket";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-sm text-slate-400">{label}</span>
      {children}
    </div>
  );
}

export default function SettingsView({
  status,
}: {
  status: ConnectionStatus;
}) {
  return (
    <section className="space-y-6 rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div>
        <h3 className="font-semibold text-slate-100">Connection</h3>
        <p className="text-xs text-slate-400">
          Backend endpoints used by the dashboard
        </p>
      </div>

      <div className="space-y-3">
        <Row label="WebSocket status">
          <span className="text-sm capitalize text-slate-200">{status}</span>
        </Row>
        <Row label="WebSocket URL">
          <code className="rounded bg-slate-950 px-2 py-0.5 text-xs text-slate-300">
            {WS_URL}
          </code>
        </Row>
        <Row label="REST API URL">
          <code className="rounded bg-slate-950 px-2 py-0.5 text-xs text-slate-300">
            {API_URL}
          </code>
        </Row>
      </div>

      <p className="rounded-md border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-400">
        To stream live data and serve historical metrics, start the backend
        with{" "}
        <code className="text-slate-300">
          uvicorn app.main:app --port 8000
        </code>
        .
      </p>
    </section>
  );
}
