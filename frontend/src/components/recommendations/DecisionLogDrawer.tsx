import { Sheet } from '@/components/ui/Sheet';
import { Badge } from '@/components/ui/Badge';
import { useRecommendationsHistory } from '@/hooks/useRecommendationsHistory';
import { urgencyColor, urgencyLabel } from '@/lib/colors';

interface DecisionLogDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function DecisionLogDrawer({ open, onClose }: DecisionLogDrawerProps) {
  const { data } = useRecommendationsHistory(20);
  const recommendations = data?.recommendations || [];

  return (
    <Sheet open={open} onClose={onClose} title="AI Decision Log">
      <div className="space-y-3">
        {recommendations.length === 0 ? (
          <p className="text-sm text-text-secondary">No scaling decisions recorded yet.</p>
        ) : (
          recommendations.map((rec: Record<string, unknown>, i: number) => {
            const type = (rec.decision_type as string) || 'unknown';
            const variant = (urgencyColor[type] || 'neutral') as 'success' | 'warning' | 'danger' | 'accent' | 'neutral';

            return (
              <div
                key={i}
                className="bg-background rounded-[8px] p-3 border border-border"
              >
                <div className="flex items-center justify-between mb-2">
                  <Badge variant={variant} size="sm">
                    {urgencyLabel[type] || type}
                  </Badge>
                  <span className="text-[10px] text-text-secondary tabular-nums">
                    {rec.timestamp
                      ? new Date(rec.timestamp as string).toLocaleString('en-US', {
                          month: 'short', day: 'numeric',
                          hour: '2-digit', minute: '2-digit', hour12: false,
                        })
                      : '—'}
                  </span>
                </div>
                <p className="text-xs text-text-secondary">{rec.reason as string}</p>
                <div className="flex gap-3 mt-2 text-[10px] text-text-secondary">
                  <span>CPU: <span className="text-text-primary">{((rec.predicted_cpu as number) ?? 0).toFixed(1)}%</span></span>
                  <span>
                    Instances: {rec.current_instances as number} → {rec.recommended_instances as number}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </Sheet>
  );
}
