import type { ReactNode } from "react";

interface ExplainProps {
  title: string;
  /** Expand by default (use for the main intro). */
  open?: boolean;
  children: ReactNode;
}

/**
 * Collapsible plain-language explainer. Uses native <details> so it needs no
 * JavaScript and stays collapsed to preserve the dense terminal layout.
 */
export default function Explain({ title, open = false, children }: ExplainProps) {
  return (
    <details open={open} className="help border border-noir-line bg-noir-panel2">
      <summary className="flex items-center gap-2 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.16em] text-noir-muted hover:text-noir-text">
        <span className="help-arrow" aria-hidden="true">
          ▸
        </span>
        {title}
      </summary>
      <div className="border-t border-noir-line px-3 py-2 text-xs leading-relaxed text-noir-muted">
        {children}
      </div>
    </details>
  );
}
