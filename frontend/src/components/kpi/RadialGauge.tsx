import { useMemo } from 'react';
import { zoneToHex } from '@/lib/colors';

interface RadialGaugeProps {
  label: string;
  value: number;
  maxValue?: number;
  predicted?: number;
  unit?: string;
  zone: 'success' | 'warning' | 'danger';
}

export function RadialGauge({
  label,
  value,
  maxValue = 100,
  predicted,
  unit = '%',
  zone,
}: RadialGaugeProps) {
  const size = 140;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const percentage = useMemo(() => Math.min(value / maxValue, 1), [value, maxValue]);
  const strokeDashoffset = useMemo(
    () => circumference * (1 - percentage),
    [circumference, percentage]
  );

  const color = zoneToHex[zone];
  const delta = predicted !== undefined ? predicted - value : undefined;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          {/* Background arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth={strokeWidth}
          />
          {/* Value arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{
              transition: 'stroke-dashoffset 0.8s ease-in-out, stroke 0.3s ease',
              filter: `drop-shadow(0 0 6px ${color}40)`,
            }}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-text-primary tabular-nums">
            {value.toFixed(1)}
          </span>
          <span className="text-[10px] text-text-secondary uppercase">{unit}</span>
        </div>
      </div>

      {/* Label */}
      <p className="text-xs font-medium text-text-secondary">{label}</p>

      {/* Delta */}
      {delta !== undefined && (
        <p
          className="text-[10px] font-semibold tabular-nums"
          style={{ color: delta > 0 ? zoneToHex.danger : zoneToHex.success }}
        >
          {delta > 0 ? '▲' : '▼'} {Math.abs(delta).toFixed(1)}{unit} in 30min
        </p>
      )}
    </div>
  );
}
