const BADGE_COLORS: Record<string, string> = {
  Low: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  Medium: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  High: "bg-red-500/15 text-red-300 border-red-500/30",
  LOW: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  MEDIUM: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  HIGH: "bg-red-500/15 text-red-300 border-red-500/30",
  CRITICAL: "bg-rose-600/20 text-rose-200 border-rose-500/40",
};

export default function RiskBadge({ level }: { level: string }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${
        BADGE_COLORS[level] ?? "bg-slate-700 text-slate-200 border-slate-600"
      }`}
    >
      {level}
    </span>
  );
}
