import { Card } from '@/components/ui/Card';
import { useModelInfo } from '@/hooks/useModelInfo';

export function ModelInfoCard() {
  const { data, isLoading } = useModelInfo();

  if (isLoading) {
    return (
      <Card>
        <h3 className="text-sm font-semibold text-text-primary mb-3">Model Info</h3>
        <p className="text-xs text-text-secondary">Loading...</p>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="text-sm font-semibold text-text-primary mb-4">Model Info</h3>
      <div className="space-y-3">
        {[
          { label: 'Model', value: data?.model_name || '—' },
          { label: 'Version', value: data?.model_version || '—' },
          { label: 'Features', value: data?.feature_count?.toString() || '—' },
          { label: 'RMSE', value: data?.rmse?.toFixed(4) || '—' },
          { label: 'MAE', value: data?.mae?.toFixed(4) || '—' },
          { label: 'Training Time', value: data?.training_time_seconds ? `${data.training_time_seconds.toFixed(1)}s` : '—' },
          { label: 'Training Date', value: data?.training_date ? new Date(data.training_date).toLocaleDateString() : '—' },
        ].map((item) => (
          <div key={item.label} className="flex justify-between items-center">
            <span className="text-xs text-text-secondary">{item.label}</span>
            <span className="text-xs text-text-primary font-medium tabular-nums">{item.value}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
