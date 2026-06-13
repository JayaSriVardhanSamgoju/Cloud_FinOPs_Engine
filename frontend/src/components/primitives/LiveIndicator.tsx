export function LiveIndicator() {
  return (
    <div className="flex items-center gap-2 font-mono text-label text-pulse">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full rounded-full bg-pulse opacity-75 animate-pulse-dot" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-pulse" />
      </span>
      LIVE
    </div>
  );
}
