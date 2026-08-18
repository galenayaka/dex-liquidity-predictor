const BADGE_STYLES: Record<string, string> = {
  Low: "border-noir-line bg-noir-panel2 text-noir-dim",
  Medium: "border-noir-line2 bg-noir-panel2 text-noir-amber",
  High: "border-noir-orange bg-noir-panel2 text-noir-orange text-glow",
  LOW: "border-noir-line bg-noir-panel2 text-noir-dim",
  MEDIUM: "border-noir-line2 bg-noir-panel2 text-noir-amber",
  HIGH: "border-noir-orange bg-noir-panel2 text-noir-orange text-glow",
  CRITICAL: "border-noir-blood bg-noir-panel2 text-noir-blood blink",
};

export default function RiskBadge({ level }: { level: string }) {
  return (
    <span
      className={`inline-block border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] ${
        BADGE_STYLES[level] ?? "border-noir-line text-noir-muted"
      }`}
    >
      {level}
    </span>
  );
}
