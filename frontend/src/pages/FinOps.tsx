import { useState } from 'react';
import * as Slider from '@radix-ui/react-slider';
import { Info } from 'lucide-react';
import * as Tooltip from '@radix-ui/react-tooltip';
import { DataCard } from '@/components/primitives/DataCard';
import { AnimatedNumber } from '@/components/primitives/AnimatedNumber';
import { AreaChart, Area, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { useStore } from '@/store/useStore';
import { useTelemetryHistory } from '@/hooks/useTelemetryHistory';

// Fake workload data for visualization since backend doesn't provide it
const workloads = [
  { name: 'API Gateway', cost: 1450 },
  { name: 'ML Inference', cost: 890 },
  { name: 'Background Workers', cost: 420 },
  { name: 'Database Nodes', cost: 310 },
].sort((a, b) => b.cost - a.cost);

export function FinOps() {
  const { region } = useStore();
  const { data: telemetry } = useTelemetryHistory(region, 24 * 60); // 24 hours
  const [lagMinutes, setLagMinutes] = useState([15]);

  const historyData = telemetry?.data || [];
  
  // Fake calculation for savings
  const predictiveEvents = 124;
  const reactiveEvents = Math.floor(predictiveEvents * (1 + lagMinutes[0] / 30));
  const estimatedSavings = (reactiveEvents - predictiveEvents) * 2.45; // $2.45 per event saved

  return (
    <div className="space-y-4">
      {/* Row 1 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <DataCard title="Cost Over Time" span="2" className="min-h-[300px]">
          <div className="h-full w-full pb-6">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={historyData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                <XAxis dataKey="timestamp" tickFormatter={(val) => new Date(val).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} stroke="var(--color-border)" tick={{ fill: 'var(--color-text-secondary)', fontSize: 10, fontFamily: 'monospace' }} />
                <YAxis stroke="var(--color-border)" tick={{ fill: 'var(--color-text-secondary)', fontSize: 10, fontFamily: 'monospace' }} />
                <RechartsTooltip contentStyle={{ backgroundColor: 'var(--color-surface-2)', borderColor: 'var(--color-border)' }} itemStyle={{ fontFamily: 'monospace', fontSize: '12px' }} />
                <Area type="monotone" dataKey="cost_per_hour" stroke="var(--color-text-tertiary)" strokeWidth={2} fill="var(--color-surface-2)" isAnimationActive={true} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </DataCard>

        <DataCard title="Cost By Workload" span="2" className="min-h-[300px]">
          <div className="h-full w-full pb-6">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={workloads} layout="vertical" margin={{ top: 0, right: 20, left: 100, bottom: 0 }}>
                <XAxis type="number" stroke="var(--color-border)" tick={{ fill: 'var(--color-text-secondary)', fontSize: 10, fontFamily: 'monospace' }} />
                <YAxis dataKey="name" type="category" stroke="none" tick={{ fill: 'var(--color-text-primary)', fontSize: 11, fontFamily: 'sans-serif' }} width={100} />
                <RechartsTooltip cursor={{ fill: 'var(--color-surface-2)' }} contentStyle={{ backgroundColor: 'var(--color-surface-2)', borderColor: 'var(--color-border)', fontFamily: 'monospace' }} />
                <Bar dataKey="cost" barSize={20} radius={[0, 4, 4, 0]}>
                  {workloads.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? 'var(--color-text-secondary)' : 'var(--color-surface-3)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </DataCard>
      </div>

      {/* Row 2: Calculator */}
      <DataCard title="Cost Savings Calculator" span="4" className="border-accent border-pulse/30 bg-surface-1/50 relative overflow-hidden">
        {/* Decorative corner accent */}
        <div className="absolute top-0 right-0 w-16 h-16 bg-pulse/5 blur-[40px] rounded-full pointer-events-none" />
        
        <div className="flex flex-col md:flex-row gap-12 items-center mt-4">
          
          <div className="flex-1 w-full max-w-sm">
            <div className="flex justify-between items-end mb-4">
              <label className="text-xs font-sans text-text-secondary uppercase tracking-widest">Reactive Scaling Lag</label>
              <span className="font-mono text-pulse text-lg">{lagMinutes[0]}m</span>
            </div>
            
            <Slider.Root
              className="relative flex items-center select-none touch-none w-full h-5"
              value={lagMinutes}
              onValueChange={setLagMinutes}
              max={60}
              min={5}
              step={5}
            >
              <Slider.Track className="bg-surface-3 relative grow rounded-full h-[3px]">
                <Slider.Range className="absolute bg-pulse rounded-full h-full" />
              </Slider.Track>
              <Slider.Thumb className="block w-4 h-4 bg-pulse rounded-full hover:bg-white focus:outline-none focus:ring-2 focus:ring-pulse/50 transition-colors cursor-grab active:cursor-grabbing" />
            </Slider.Root>
            <div className="flex justify-between mt-2 text-[10px] font-mono text-text-tertiary">
              <span>5m</span>
              <span>60m</span>
            </div>
          </div>

          <div className="flex-1 w-full grid grid-cols-3 gap-6 border-l border-border pl-12">
            <div>
              <p className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider mb-2">Predictive Events</p>
              <AnimatedNumber value={predictiveEvents} decimals={0} size="data-md" />
            </div>
            <div>
              <p className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider mb-2">Reactive Equivalent</p>
              <AnimatedNumber value={reactiveEvents} decimals={0} size="data-md" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-2">
                <p className="text-[10px] font-mono text-pulse uppercase tracking-wider">Est. Savings</p>
                <Tooltip.Provider>
                  <Tooltip.Root>
                    <Tooltip.Trigger>
                      <Info className="w-3 h-3 text-text-tertiary hover:text-text-primary" />
                    </Tooltip.Trigger>
                    <Tooltip.Portal>
                      <Tooltip.Content className="bg-surface-3 border border-border px-3 py-2 rounded text-xs font-mono text-text-primary max-w-xs z-50 animate-slide-up-fade" sideOffset={5}>
                        Formula: (ReactiveEvents - PredictiveEvents) * AvgEventCost
                        <Tooltip.Arrow className="fill-surface-3" />
                      </Tooltip.Content>
                    </Tooltip.Portal>
                  </Tooltip.Root>
                </Tooltip.Provider>
              </div>
              <AnimatedNumber value={estimatedSavings} prefix="$" decimals={2} size="data-xl" />
            </div>
          </div>
          
        </div>
      </DataCard>
    </div>
  );
}
