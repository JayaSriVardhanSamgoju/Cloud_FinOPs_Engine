import { RadialGauge } from './RadialGauge';
import { Card } from '@/components/ui/Card';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { cpuZone, ramZone, costZone } from '@/lib/colors';

interface KpiRowProps {
  cpuUsage?: number;
  ramUsage?: number;
  costPerHour?: number;
  predictedCpu?: number;
  slaRisk?: number;
  activeInstances?: number;
  isLoading?: boolean;
}

export function KpiRow({
  cpuUsage = 0,
  ramUsage = 0,
  costPerHour = 0,
  predictedCpu,
  slaRisk = 0,
  activeInstances = 0,
  isLoading = false,
}: KpiRowProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-3 lg:grid-cols-6 gap-4">
        {[...Array(6)].map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 lg:grid-cols-6 gap-4">
      {/* CPU Gauge */}
      <Card className="flex justify-center">
        <RadialGauge
          label="CPU Usage"
          value={cpuUsage}
          predicted={predictedCpu}
          zone={cpuZone(cpuUsage)}
        />
      </Card>

      {/* RAM Gauge */}
      <Card className="flex justify-center">
        <RadialGauge
          label="RAM Usage"
          value={ramUsage}
          zone={ramZone(ramUsage)}
        />
      </Card>

      {/* Cost Gauge */}
      <Card className="flex justify-center">
        <RadialGauge
          label="Cost / Hour"
          value={costPerHour}
          maxValue={10}
          unit="$/hr"
          zone={costZone(costPerHour)}
        />
      </Card>

      {/* Predicted CPU */}
      <Card className="flex flex-col items-center justify-center text-center">
        <p className="text-xs text-text-secondary mb-1">Predicted CPU</p>
        <p className="text-3xl font-bold text-accent tabular-nums">
          {predictedCpu?.toFixed(1) ?? '—'}
        </p>
        <p className="text-[10px] text-text-secondary mt-1">30 min forecast</p>
      </Card>

      {/* SLA Risk */}
      <Card className="flex flex-col items-center justify-center text-center">
        <p className="text-xs text-text-secondary mb-1">SLA Risk</p>
        <p className={`text-3xl font-bold tabular-nums ${
          slaRisk > 70 ? 'text-danger' : slaRisk > 40 ? 'text-warning' : 'text-success'
        }`}>
          {slaRisk.toFixed(1)}
        </p>
        <p className="text-[10px] text-text-secondary mt-1">Breach Score</p>
      </Card>

      {/* Active Instances */}
      <Card className="flex flex-col items-center justify-center text-center">
        <p className="text-xs text-text-secondary mb-1">Instances</p>
        <p className="text-3xl font-bold text-info tabular-nums">
          {activeInstances}
        </p>
        <p className="text-[10px] text-text-secondary mt-1">Active</p>
      </Card>
    </div>
  );
}
