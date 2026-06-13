import CountUpModule from "react-countup";
const CountUp = (CountUpModule as any).default || CountUpModule;

interface AnimatedNumberProps {
  value: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
  size?: "data-xl" | "data-lg" | "data-md";
  trend?: number; // positive/negative delta — renders a small arrow + color
}

export function AnimatedNumber({ value, decimals = 1, suffix = "", prefix = "", size = "data-lg", trend }: AnimatedNumberProps) {
  return (
    <div className="flex items-baseline gap-2">
      <span className={`font-mono ${size} text-text-primary data-value`}>
        <CountUp end={value} decimals={decimals} duration={0.8} prefix={prefix} suffix={suffix} preserveValue />
      </span>
      {trend !== undefined && (
        <span className={`font-mono text-sm ${trend >= 0 ? "text-status-critical" : "text-pulse"}`}>
          {trend >= 0 ? "▲" : "▼"} {Math.abs(trend).toFixed(1)}
        </span>
      )}
    </div>
  );
}
