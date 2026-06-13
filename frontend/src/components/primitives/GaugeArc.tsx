import { useEffect, useState } from "react";
import CountUpModule from "react-countup";
const CountUp = (CountUpModule as any).default || CountUpModule;

interface GaugeArcProps {
  value: number; // 0 to 100
  label?: string;
  predicted?: number; // predicted value to show below
}

export function GaugeArc({ value, label, predicted }: GaugeArcProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 10);
    return () => clearTimeout(timer);
  }, []);

  const clampedValue = Math.min(100, Math.max(0, value));
  
  // 270 degree arc, radius 40
  // Length = 2 * PI * 40 * 0.75 = 188.5
  const circumference = 188.5;
  const strokeDashoffset = circumference - (clampedValue / 100) * circumference;

  // Determine color zone
  let strokeColor = "stroke-status-healthy";
  if (clampedValue >= 75 && clampedValue < 85) strokeColor = "stroke-status-warning";
  if (clampedValue >= 85) strokeColor = "stroke-status-critical";

  return (
    <div className="flex flex-col items-center justify-center relative w-full h-full min-h-[140px]">
      <div className="relative w-32 h-32">
        <svg viewBox="0 0 100 100" className="w-full h-full drop-shadow-md">
          {/* Background Track */}
          <path
            d="M 21.72 78.28 A 40 40 0 1 1 78.28 78.28"
            fill="none"
            stroke="var(--color-surface-3, #1E222B)"
            strokeWidth="8"
            strokeLinecap="round"
          />
          
          {/* Ticks at 0, 25, 50, 75, 100 */}
          {/* 0% (225deg) */}
          <line x1="18.18" y1="81.82" x2="25.25" y2="74.75" stroke="#5A5E6B" strokeWidth="1" />
          {/* 25% (292.5deg) */}
          <line x1="6.17" y1="33.43" x2="14.36" y2="36.83" stroke="#5A5E6B" strokeWidth="1" />
          {/* 50% (0deg top) */}
          <line x1="50" y1="5" x2="50" y2="15" stroke="#5A5E6B" strokeWidth="1" />
          {/* 75% (67.5deg) */}
          <line x1="93.83" y1="33.43" x2="85.64" y2="36.83" stroke="#5A5E6B" strokeWidth="1" />
          {/* 100% (135deg) */}
          <line x1="81.82" y1="81.82" x2="74.75" y2="74.75" stroke="#5A5E6B" strokeWidth="1" />

          {/* Fill Arc */}
          <path
            d="M 21.72 78.28 A 40 40 0 1 1 78.28 78.28"
            fill="none"
            className={`${strokeColor} transition-all duration-800 ease-out`}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={mounted ? strokeDashoffset : circumference}
            style={{ 
              transition: mounted ? "stroke-dashoffset 0.8s ease-out, stroke 0.3s ease-out" : "none",
            }}
          />
        </svg>

        {/* Center Text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pt-2">
          <span className="font-mono text-data-lg text-text-primary data-value">
            <CountUp end={clampedValue} decimals={1} duration={0.8} preserveValue />%
          </span>
          {label && <span className="text-label text-text-tertiary mt-1 uppercase tracking-widest">{label}</span>}
        </div>
      </div>
      
      {/* Prediction Sub-label */}
      {predicted !== undefined && (
        <div className="mt-2 text-[11px] font-mono text-text-secondary bg-surface-2 px-2 py-0.5 rounded border border-border">
          → <CountUp end={predicted} decimals={1} duration={0.8} preserveValue />% in 30m
        </div>
      )}
    </div>
  );
}
