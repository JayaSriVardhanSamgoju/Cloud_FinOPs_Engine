const statusConfig = {
  healthy:  { color: "text-status-healthy",  dot: "bg-status-healthy",  label: "OPERATIONAL" },
  warning:  { color: "text-status-warning",  dot: "bg-status-warning",  label: "ELEVATED" },
  critical: { color: "text-status-critical", dot: "bg-status-critical", label: "CRITICAL" },
  info:     { color: "text-status-info",     dot: "bg-status-info",     label: "INFO" },
};

export function StatusPill({ status, label }: { status: keyof typeof statusConfig; label?: string }) {
  const cfg = statusConfig[status];
  return (
    <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded border border-border bg-surface-2">
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} ${status === "critical" ? "animate-pulse-dot" : ""}`} />
      <span className={`text-label ${cfg.color} font-mono`}>{label ?? cfg.label}</span>
    </div>
  );
}
