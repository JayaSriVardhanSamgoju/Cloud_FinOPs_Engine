import React from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { GaugeArc } from '@/components/primitives/GaugeArc';
import { AnimatedNumber } from '@/components/primitives/AnimatedNumber';
import { DataCard } from '@/components/primitives/DataCard';

export function KpiStrip({ telemetry }: { telemetry: any }) {
  const t = telemetry || {};
  const currentCost = t.cost_per_hour || 0;
  const activeInstances = t.active_instances || 0;
  
  // Instance Grid (Server Rack visual metaphor)
  const maxInstances = 20;
  const blocks = Array.from({ length: maxInstances }).map((_, i) => i < activeInstances);

  // Fake cost sparkline data for visual
  const sparkData = React.useMemo(() => 
    Array.from({ length: 12 }).map((_, i) => ({ val: currentCost * (0.9 + Math.random() * 0.2) })),
  [currentCost]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 w-full">
      <DataCard title="CPU Utilization">
        <GaugeArc value={t.cpu_usage || 0} predicted={t.predicted_cpu_30min} />
      </DataCard>

      <DataCard title="Memory">
        <GaugeArc value={t.ram_usage || 0} label="RAM" />
      </DataCard>

      <DataCard title="Cost Rate">
        <div className="flex flex-col h-full justify-between pb-2">
          <AnimatedNumber value={currentCost} prefix="$" suffix="/HR" decimals={2} trend={-0.15} />
          
          <div className="h-[60px] w-full mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sparkData}>
                <Line type="monotone" dataKey="val" stroke="var(--color-text-secondary)" strokeWidth={1} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </DataCard>

      <DataCard title="Active Instances">
        <div className="flex flex-col h-full justify-between pb-2">
          <div className="font-mono text-data-xl text-text-primary">{activeInstances}</div>
          
          <div className="grid grid-cols-5 gap-1 mt-4 opacity-80">
            {blocks.map((active, i) => (
              <div 
                key={i} 
                className={`w-full aspect-square rounded-[2px] transition-colors duration-500 ${active ? 'bg-pulse' : 'bg-surface-3'}`}
              />
            ))}
          </div>
        </div>
      </DataCard>
    </div>
  );
}
