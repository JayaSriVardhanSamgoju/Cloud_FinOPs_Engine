import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useDriftStatus, useTriggerDrift } from '@/hooks/useDriftStatus';

export function DriftStatusCard() {
  const { data, isLoading } = useDriftStatus();
  const { mutate: triggerDrift, isPending } = useTriggerDrift();

  const driftDetected = data?.drift_detected;
  const driftScore = data?.drift_score;
  const threshold = data?.threshold ?? 7.0;

  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text-primary">Drift Monitor</h3>
        {!isLoading && (
          <Badge variant={driftDetected ? 'danger' : 'success'} size="md">
            {driftDetected ? 'DRIFT DETECTED' : 'STABLE'}
          </Badge>
        )}
      </div>

      {driftScore !== null && driftScore !== undefined ? (
        <div className="space-y-3">
          {/* Drift gauge bar */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-text-secondary">RMSE</span>
              <span className="text-text-primary font-semibold">{driftScore.toFixed(2)}</span>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min((driftScore / (threshold * 2)) * 100, 100)}%`,
                  backgroundColor: driftDetected ? '#FF3D71' : '#00D68F',
                }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-text-secondary mt-1">
              <span>0</span>
              <span className="text-danger">Threshold: {threshold}</span>
              <span>{(threshold * 2).toFixed(0)}</span>
            </div>
          </div>

          {/* Last checked */}
          {data?.checked_at && (
            <p className="text-[10px] text-text-secondary">
              Last checked: {new Date(data.checked_at).toLocaleString()}
            </p>
          )}

          {/* Trigger button */}
          <button
            onClick={() => triggerDrift()}
            disabled={isPending}
            className="w-full py-2 text-xs font-semibold rounded-[8px] border transition-colors
              border-accent/30 text-accent hover:bg-accent/10 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPending ? 'Running...' : 'Run Drift Check Now'}
          </button>
        </div>
      ) : (
        <p className="text-sm text-text-secondary">{data?.message || 'Loading...'}</p>
      )}
    </Card>
  );
}
