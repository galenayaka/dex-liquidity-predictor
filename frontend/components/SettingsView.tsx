"use client";

import type { ReactNode } from "react";
import { useTheme } from "@/components/ThemeProvider";
import type { ConnectionStatus } from "@/hooks/useWebSocket";
import { THEMES } from "@/lib/themes";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-noir-line px-3 py-2 last:border-0">
      <span className="text-xs uppercase tracking-[0.14em] text-noir-dim">
        {label}
      </span>
      {children}
    </div>
  );
}

export default function SettingsView({
  status,
}: {
  status: ConnectionStatus;
}) {
  const { theme, setTheme } = useTheme();

  return (
    <div className="max-w-2xl space-y-3">
      <section className="panel">
        <div className="panel-head">
          <h3 className="panel-title">Connection</h3>
          <p className="panel-sub">Backend endpoints</p>
        </div>

        <div>
          <Row label="WebSocket status">
            <span className="text-xs font-bold uppercase tracking-wider text-noir-amber">
              {status}
            </span>
          </Row>
          <Row label="WebSocket URL">
            <code className="text-xs text-noir-orange">{WS_URL}</code>
          </Row>
          <Row label="REST API URL">
            <code className="text-xs text-noir-orange">{API_URL}</code>
          </Row>
        </div>

        <p className="border-t border-noir-line px-3 py-2 text-[10px] uppercase tracking-wider text-noir-dim">
          Start backend:{" "}
          <code className="text-noir-muted">
            uvicorn app.main:app --port 8000
          </code>
        </p>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h3 className="panel-title">Color Theme</h3>
          <p className="panel-sub">Terminal palette</p>
        </div>
        <div className="flex flex-wrap gap-2 p-3">
          {THEMES.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTheme(t.id)}
              className={`flex items-center gap-2 border px-2 py-1 text-[10px] uppercase tracking-[0.14em] transition-colors ${
                theme === t.id
                  ? "border-noir-accent bg-noir-panel2 text-noir-accent"
                  : "border-noir-line text-noir-muted hover:border-noir-line2 hover:text-noir-text"
              }`}
            >
              <span
                className="h-3 w-3 border border-noir-line"
                style={{ backgroundColor: t.swatch }}
                aria-hidden="true"
              />
              {t.label}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
