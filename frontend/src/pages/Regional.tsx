import { useRegionalSummary } from '@/hooks/useRegionalSummary';
import { useStore } from '@/store/useStore';
import { DataCard } from '@/components/primitives/DataCard';
import { StatusPill } from '@/components/primitives/StatusPill';
import { GaugeArc } from '@/components/primitives/GaugeArc';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

export function Regional() {
  const { data } = useRegionalSummary();
  const { region, setRegion } = useStore();
  const regions = data?.regions || [];

  return (
    <div className="space-y-4">
      {/* Row 1: Region Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {regions.slice(0, 3).map((r: any) => {
          const isSelected = region === r.region;
          
          return (
            <div 
              key={r.region} 
              onClick={() => setRegion(r.region)}
              className="cursor-pointer"
            >
              <DataCard 
                title={r.region} 
                accent={isSelected}
                className={`min-h-[320px] transition-all duration-300 ${isSelected ? 'bg-surface-2 shadow-[0_0_20px_rgba(94,255,176,0.05)]' : 'hover:bg-surface-2'}`}
              >
                <div className="absolute top-5 right-5">
                  <StatusPill status={r.avg_cpu > 80 ? 'critical' : r.avg_cpu > 60 ? 'warning' : 'healthy'} />
                </div>
                
                <div className="mt-8 mb-6">
                  <GaugeArc value={r.avg_cpu || 0} label="AVG CPU" />
                </div>
                
                <div className="space-y-3 font-mono text-sm border-t border-border pt-4">
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">Avg Cost/Hr</span>
                    <span className="text-text-primary">${(r.avg_cost || 0).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">Request Rate</span>
                    <span className="text-text-primary">{(r.avg_request_rate || 0).toFixed(0)} RPS</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">24h Anomalies</span>
                    <span className="text-status-warning">{r.anomaly_count || 0}</span>
                  </div>
                </div>

                <div className="h-[40px] w-full mt-4 opacity-50">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={(r.cpu_sparkline || []).map((v: number, i: number) => ({ i, v }))}>
                      <Line type="monotone" dataKey="v" stroke="var(--color-text-secondary)" strokeWidth={1} dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </DataCard>
            </div>
          );
        })}
      </div>

      {/* Row 2: Comparison Table */}
      <DataCard title="Cross-Region Comparison" span="4">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border">
                <th className="py-3 px-4 text-[10px] font-mono text-text-tertiary uppercase tracking-widest font-medium">Metric</th>
                {regions.map((r: any) => (
                  <th key={r.region} className="py-3 px-4 text-[10px] font-mono text-text-tertiary uppercase tracking-widest font-medium">{r.region}</th>
                ))}
              </tr>
            </thead>
            <tbody className="font-mono text-sm text-text-primary">
              <tr className="border-b border-border/50 hover:bg-surface-2/50 transition-colors">
                <td className="py-3 px-4 text-text-secondary font-sans text-xs uppercase tracking-widest">CPU Usage</td>
                {regions.map((r: any) => <td key={r.region} className="py-3 px-4">{(r.avg_cpu || 0).toFixed(1)}%</td>)}
              </tr>
              <tr className="border-b border-border/50 hover:bg-surface-2/50 transition-colors">
                <td className="py-3 px-4 text-text-secondary font-sans text-xs uppercase tracking-widest">Cost / Hr</td>
                {regions.map((r: any) => <td key={r.region} className="py-3 px-4">${(r.avg_cost || 0).toFixed(2)}</td>)}
              </tr>
              <tr className="border-b border-border/50 hover:bg-surface-2/50 transition-colors">
                <td className="py-3 px-4 text-text-secondary font-sans text-xs uppercase tracking-widest">Request Rate</td>
                {regions.map((r: any) => <td key={r.region} className="py-3 px-4">{(r.avg_request_rate || 0).toFixed(0)}</td>)}
              </tr>
              <tr className="hover:bg-surface-2/50 transition-colors">
                <td className="py-3 px-4 text-text-secondary font-sans text-xs uppercase tracking-widest">Anomalies</td>
                {regions.map((r: any) => <td key={r.region} className="py-3 px-4 text-status-warning">{r.anomaly_count || 0}</td>)}
              </tr>
            </tbody>
          </table>
        </div>
      </DataCard>
    </div>
  );
}
