import { useState } from 'react';
import { useHealth } from '@/hooks/useHealth';
import { DataCard } from '@/components/primitives/DataCard';
import { StatusPill } from '@/components/primitives/StatusPill';
import { AnimatedNumber } from '@/components/primitives/AnimatedNumber';
import { useToastStore } from '@/components/layout/Toast';

const modelsData = [
  { name: 'XGBoost (Prod)', rmse: 6.24, mae: 4.81, r2: 0.92, impr: '+14.5%', isWinner: true },
  { name: 'Random Forest', rmse: 6.81, mae: 5.12, r2: 0.89, impr: '+6.2%', isWinner: false },
  { name: 'LightGBM', rmse: 6.35, mae: 4.90, r2: 0.91, impr: '+12.8%', isWinner: false },
  { name: 'Linear Regression', rmse: 8.42, mae: 6.75, r2: 0.76, impr: '-15.4%', isWinner: false },
  { name: 'Persistence (Baseline)', rmse: 7.29, mae: 5.88, r2: 0.84, impr: '0.0%', isWinner: false },
];

export function ModelHealth() {
  const { data: health } = useHealth();
  const [isChecking, setIsChecking] = useState(false);
  const { addToast } = useToastStore();

  const handleDriftCheck = () => {
    setIsChecking(true);
    // Simulate API call
    setTimeout(() => {
      setIsChecking(false);
      addToast('Drift analysis complete. Model is stable.', 'success');
    }, 1500);
  };

  return (
    <div className="space-y-4">
      {/* Row 1 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <DataCard title="Model Metadata" span="2">
          <div className="grid grid-cols-2 gap-y-4 mt-4">
            <div>
              <span className="block text-[10px] font-mono text-text-tertiary uppercase tracking-widest mb-1">Architecture</span>
              <span className="font-mono text-sm text-text-primary">XGBoost Regressor</span>
            </div>
            <div>
              <span className="block text-[10px] font-mono text-text-tertiary uppercase tracking-widest mb-1">Version</span>
              <span className="font-mono text-sm text-text-primary">{health?.model_version || 'v2.0'}</span>
            </div>
            <div>
              <span className="block text-[10px] font-mono text-text-tertiary uppercase tracking-widest mb-1">Last Trained</span>
              <span className="font-mono text-sm text-text-primary">2024-06-12 04:30 UTC</span>
            </div>
            <div>
              <span className="block text-[10px] font-mono text-text-tertiary uppercase tracking-widest mb-1">Features</span>
              <span className="font-mono text-sm text-text-primary">24 Dense</span>
            </div>
          </div>
        </DataCard>

        <DataCard title="Drift Status" span="2" className="flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <StatusPill status="healthy" label="STABLE" />
            <div className="text-right">
              <span className="block text-[10px] font-mono text-text-tertiary uppercase tracking-widest mb-1">Current RMSE</span>
              <AnimatedNumber value={6.32} decimals={2} size="data-md" />
            </div>
          </div>
          
          <div className="mt-8 flex items-center justify-between border-t border-border pt-4">
            <span className="text-[10px] font-mono text-text-tertiary">Last checked: 2 hours ago</span>
            <button 
              onClick={handleDriftCheck}
              disabled={isChecking}
              className="flex items-center gap-2 px-4 py-2 text-[10px] font-mono uppercase tracking-widest border border-pulse text-pulse hover:bg-pulse hover:text-surface-0 transition-colors rounded disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isChecking && (
                <svg className="animate-spin -ml-1 mr-2 h-3 w-3 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
              {isChecking ? 'Analyzing...' : 'Run Drift Check'}
            </button>
          </div>
        </DataCard>
      </div>

      {/* Row 2 */}
      <DataCard title="Model Selection & Ablation" span="4">
        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border">
                <th className="py-3 px-4 text-[10px] font-mono text-text-tertiary uppercase tracking-widest font-medium">Model Candidate</th>
                <th className="py-3 px-4 text-[10px] font-mono text-text-tertiary uppercase tracking-widest font-medium">RMSE</th>
                <th className="py-3 px-4 text-[10px] font-mono text-text-tertiary uppercase tracking-widest font-medium">MAE</th>
                <th className="py-3 px-4 text-[10px] font-mono text-text-tertiary uppercase tracking-widest font-medium">R²</th>
                <th className="py-3 px-4 text-[10px] font-mono text-text-tertiary uppercase tracking-widest font-medium text-right">vs Baseline</th>
              </tr>
            </thead>
            <tbody className="font-mono text-sm">
              {modelsData.map((m, i) => (
                <tr key={i} className={`border-b border-border/50 transition-colors ${m.isWinner ? 'bg-surface-2/30 border-l-2 border-l-pulse' : 'hover:bg-surface-2/50 border-l-2 border-l-transparent'}`}>
                  <td className={`py-3 px-4 ${m.isWinner ? 'text-pulse' : 'text-text-primary'}`}>{m.name}</td>
                  <td className="py-3 px-4 text-text-secondary">{m.rmse.toFixed(2)}</td>
                  <td className="py-3 px-4 text-text-secondary">{m.mae.toFixed(2)}</td>
                  <td className="py-3 px-4 text-text-secondary">{m.r2.toFixed(2)}</td>
                  <td className={`py-3 px-4 text-right ${m.impr.startsWith('+') ? 'text-status-healthy' : m.impr.startsWith('-') ? 'text-status-critical' : 'text-text-tertiary'}`}>{m.impr}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataCard>
    </div>
  );
}
