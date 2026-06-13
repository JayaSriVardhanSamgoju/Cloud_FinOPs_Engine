import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts';
import { motion } from 'framer-motion';

export function OverviewHeroChart({ data }: { data: any[] }) {
  if (!data || data.length === 0) {
    return (
      <div className="h-64 w-full flex items-center justify-center text-text-secondary font-mono text-sm">
        WAITING FOR TELEMETRY...
      </div>
    );
  }

  // Find anomalies for ReferenceDots
  const anomalies = data.filter(d => d.anomaly_score > 0.8 || d.predicted_cpu_30min > 85);

  return (
    <div className="h-72 w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-pulse)" stopOpacity={0.2} />
              <stop offset="95%" stopColor="var(--color-pulse)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis 
            dataKey="timestamp" 
            tickFormatter={(val) => new Date(val).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            stroke="var(--color-border)"
            tick={{ fill: 'var(--color-text-secondary)', fontSize: 10, fontFamily: 'monospace' }}
            tickMargin={10}
          />
          <YAxis 
            yAxisId="left"
            stroke="var(--color-border)"
            tick={{ fill: 'var(--color-text-secondary)', fontSize: 10, fontFamily: 'monospace' }}
            domain={[0, 100]}
          />
          <YAxis 
            yAxisId="right" 
            orientation="right"
            stroke="var(--color-border)"
            tick={{ fill: 'var(--color-text-secondary)', fontSize: 10, fontFamily: 'monospace' }}
            hide
          />
          <Tooltip 
            contentStyle={{ backgroundColor: 'var(--color-surface-2)', borderColor: 'var(--color-border)', borderRadius: '6px' }}
            itemStyle={{ fontFamily: 'monospace', fontSize: '12px' }}
            labelStyle={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--color-text-tertiary)', marginBottom: '4px' }}
          />
          
          <Area
            yAxisId="left"
            type="monotone"
            dataKey="cpu_usage"
            stroke="var(--color-pulse)"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorCpu)"
            isAnimationActive={true}
            animationDuration={1500}
            animationEasing="ease-out"
          />
          <Area
            yAxisId="right"
            type="monotone"
            dataKey="response_latency_ms"
            stroke="var(--color-status-info)"
            strokeWidth={1}
            strokeDasharray="4 4"
            fill="none"
            isAnimationActive={true}
            animationDuration={1500}
          />

          {anomalies.map((entry, index) => (
            <ReferenceDot
              key={`anomaly-${index}`}
              yAxisId="left"
              x={entry.timestamp}
              y={entry.cpu_usage}
              r={4}
              fill="var(--color-status-critical)"
              stroke="var(--color-surface-0)"
              strokeWidth={2}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
