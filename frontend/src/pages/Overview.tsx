import { useState } from 'react';
import { useStore } from '@/store/useStore';
import { useTelemetryHistory } from '@/hooks/useTelemetryHistory';
import { usePrediction } from '@/hooks/usePrediction';
import { useRecommendationsHistory } from '@/hooks/useRecommendationsHistory';
import { DataCard } from '@/components/primitives/DataCard';
import { AlertTriangle } from 'lucide-react';
import { KpiStrip } from '@/components/overview/KpiStrip';
import { OverviewHeroChart } from '@/components/overview/OverviewHeroChart';
import { RecommendationCard } from '@/components/overview/RecommendationCard';
import { AnomalyFeed } from '@/components/overview/AnomalyFeed';
import { RegionalStrips } from '@/components/overview/RegionalStrips';

export function Overview() {
  const { region } = useStore();
  const [timeRange, setTimeRange] = useState(1); // Hours
  
  const { data: telemetry, isError, refetch } = useTelemetryHistory(region, timeRange);
  const { data: prediction } = usePrediction(region);
  const { data: recommendations } = useRecommendationsHistory(10);

  const historyData = telemetry?.data || [];
  const latestPrediction = prediction;
  const latestRec = recommendations?.logs?.[0];

  if (isError) {
    return (
      <div className="flex h-full items-center justify-center">
        <DataCard title="Service Unavailable" className="flex flex-col items-center p-8 max-w-sm text-center">
          <AlertTriangle className="w-8 h-8 text-status-warning mb-4" />
          <p className="text-sm font-sans text-text-secondary mb-6">Unable to reach prediction service. Is the backend running?</p>
          <button 
            onClick={() => refetch()}
            className="px-4 py-2 font-mono text-sm text-pulse border border-pulse rounded hover:bg-pulse/10 transition-colors"
          >
            RETRY
          </button>
        </DataCard>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Row 1: KPI Strip */}
      <KpiStrip telemetry={{ ...historyData[historyData.length - 1], predicted_cpu_30min: latestPrediction?.predicted_cpu_30min }} />

      {/* Row 2: Hero Chart & Recommendation */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <DataCard title="Infrastructure Timeline" span="3" className="relative min-h-[360px]">
          <div className="absolute top-5 right-5 flex gap-1">
            {[1, 6, 24, 168].map(h => (
              <button 
                key={h}
                onClick={() => setTimeRange(h)}
                className={`px-2 py-1 text-[10px] font-mono rounded border transition-colors ${timeRange === h ? 'bg-surface-2 border-pulse text-pulse' : 'border-border text-text-tertiary hover:text-text-primary hover:border-border-hover'}`}
              >
                {h === 168 ? '7D' : `${h}H`}
              </button>
            ))}
          </div>
          <OverviewHeroChart data={historyData} />
        </DataCard>
        
        <DataCard title="System Recommendation" span="1" accent>
          <RecommendationCard recommendation={latestRec} />
        </DataCard>
      </div>

      {/* Row 3: Anomalies & Regional */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <DataCard title="Anomaly Feed" span="2">
          <AnomalyFeed history={historyData} />
        </DataCard>
        
        <DataCard title="Regional Distribution" span="2">
          <RegionalStrips />
        </DataCard>
      </div>
    </div>
  );
}
