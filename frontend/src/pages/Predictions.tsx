import { useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { useStore } from '@/store/useStore';
import { usePredictionsHistory } from '@/hooks/usePredictionsHistory';
import { DataCard } from '@/components/primitives/DataCard';
import { AnimatedNumber } from '@/components/primitives/AnimatedNumber';

// Fake SHAP data to demonstrate UI since backend doesn't provide it yet
const fakeShapData = [
  { feature: 'cpu_usage_lag_1', impact: 15.2 },
  { feature: 'resource_pressure_score', impact: 8.7 },
  { feature: 'active_instances', impact: -4.3 },
  { feature: 'is_weekend', impact: -12.1 },
  { feature: 'request_rate_lag_1', impact: 3.4 },
  { feature: 'cost_per_hour', impact: -1.2 },
].sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact));

export function Predictions() {
  const { region } = useStore();
  const [target, setTarget] = useState('cpu30');
  const { data } = usePredictionsHistory(region, 60);

  const predictions = data?.predictions || [];
  
  // Calculate current RMSE from recent data
  const rmse = predictions.length > 0 
    ? Math.sqrt(predictions.reduce((acc: number, p: any) => acc + Math.pow((p.actual_cpu || 0) - p.predicted_cpu, 2), 0) / predictions.length)
    : 0;

  return (
    <div className="space-y-4">
      {/* Row 1 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <DataCard title="Prediction Accuracy" span="3" className="min-h-[400px] flex flex-col">
          <Tabs.Root value={target} onValueChange={setTarget} className="mb-4">
            <Tabs.List className="flex gap-2 border-b border-border pb-2">
              {[
                { id: 'cpu30', label: 'CPU 30m' },
                { id: 'cpu60', label: 'CPU 1h' },
                { id: 'rps', label: 'Request Rate' },
                { id: 'lat', label: 'Latency' },
              ].map(t => (
                <Tabs.Trigger 
                  key={t.id} 
                  value={t.id}
                  className="px-3 py-1 text-xs font-mono rounded-t text-text-secondary hover:text-text-primary data-[state=active]:bg-surface-2 data-[state=active]:text-pulse transition-colors"
                >
                  {t.label}
                </Tabs.Trigger>
              ))}
            </Tabs.List>
          </Tabs.Root>

          <div className="flex-1 w-full min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={predictions} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                <XAxis dataKey="timestamp" tickFormatter={(val) => new Date(val).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} stroke="var(--color-border)" tick={{ fill: 'var(--color-text-secondary)', fontSize: 10, fontFamily: 'monospace' }} />
                <YAxis stroke="var(--color-border)" tick={{ fill: 'var(--color-text-secondary)', fontSize: 10, fontFamily: 'monospace' }} />
                <Tooltip contentStyle={{ backgroundColor: 'var(--color-surface-2)', borderColor: 'var(--color-border)' }} itemStyle={{ fontFamily: 'monospace', fontSize: '12px' }} />
                
                {/* Gap shading */}
                <Area type="monotone" dataKey="actual_cpu" stroke="none" fill="var(--color-border)" fillOpacity={0.1} />
                
                <Area type="monotone" dataKey="actual_cpu" stroke="var(--color-text-secondary)" strokeWidth={1.5} fill="none" isAnimationActive={true} />
                <Area type="monotone" dataKey="predicted_cpu" stroke="var(--color-pulse)" strokeWidth={2} fill="none" isAnimationActive={true} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </DataCard>

        <DataCard title="Model Error" span="1" accent>
          <div className="flex flex-col h-full justify-between pb-4">
            <div>
              <p className="text-xs text-text-tertiary font-mono mb-2">ROLLING RMSE</p>
              <AnimatedNumber value={rmse} decimals={2} />
            </div>
            
            <div className="mt-8">
              <div className="flex justify-between text-[10px] font-mono text-text-secondary mb-2">
                <span>0.0</span>
                <span>Threshold: 7.0</span>
              </div>
              <div className="h-2 w-full bg-surface-3 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-1000 ${rmse > 7 ? 'bg-status-critical' : rmse > 5 ? 'bg-status-warning' : 'bg-status-healthy'}`} 
                  style={{ width: `${Math.min(100, (rmse / 7) * 100)}%` }} 
                />
              </div>
            </div>
          </div>
        </DataCard>
      </div>

      {/* Row 2 */}
      <DataCard title="Why This Prediction?" span="4" className="min-h-[300px]">
        <div className="flex items-center gap-4 text-[10px] font-mono text-text-tertiary mb-6 uppercase tracking-widest">
          <span className="flex items-center gap-1"><div className="w-2 h-2 bg-status-info"></div> Negative Impact</span>
          <span className="flex items-center gap-1"><div className="w-2 h-2 bg-pulse"></div> Positive Impact</span>
        </div>
        
        <div className="h-[250px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={fakeShapData} layout="vertical" margin={{ top: 0, right: 30, left: 140, bottom: 0 }}>
              <XAxis type="number" stroke="var(--color-border)" tick={{ fill: 'var(--color-text-secondary)', fontSize: 10, fontFamily: 'monospace' }} />
              <YAxis dataKey="feature" type="category" stroke="none" tick={{ fill: 'var(--color-text-primary)', fontSize: 11, fontFamily: 'monospace' }} width={140} />
              <Tooltip cursor={{ fill: 'var(--color-surface-2)' }} contentStyle={{ backgroundColor: 'var(--color-surface-2)', borderColor: 'var(--color-border)', fontFamily: 'monospace' }} />
              
              <Bar dataKey="impact" barSize={24} isAnimationActive={true} animationDuration={1000}>
                {fakeShapData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.impact > 0 ? 'var(--color-pulse)' : 'var(--color-status-info)'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </DataCard>
    </div>
  );
}
