import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DecisionLogDrawer } from './DecisionLogDrawer';
import { urgencyColor, urgencyLabel } from '@/lib/colors';

interface RecommendationCardProps {
  recommendation?: {
    recommendation: string;
    reason: string;
    urgency?: string;
    current_instances?: number;
    target_instances?: number;
    instances_to_add?: number;
    instances_to_remove?: number;
  };
}

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  if (!recommendation) return null;

  const type = recommendation.recommendation || 'unknown';
  const variant = (urgencyColor[type] || 'neutral') as 'success' | 'warning' | 'danger' | 'accent' | 'neutral';
  const label = urgencyLabel[type] || type.toUpperCase();

  const instanceDelta = recommendation.instances_to_add
    ? `+${recommendation.instances_to_add}`
    : recommendation.instances_to_remove
    ? `-${recommendation.instances_to_remove}`
    : '0';

  return (
    <>
      <Card hover onClick={() => setDrawerOpen(true)}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-text-primary">AI Recommendation</h3>
          <span className="text-[10px] text-text-secondary">Click for history →</span>
        </div>

        <Badge variant={variant} size="md">
          {label}
        </Badge>

        <p className="text-sm text-text-secondary mt-3">{recommendation.reason}</p>

        <div className="flex items-center gap-4 mt-3">
          <div className="text-xs text-text-secondary">
            Instances: <span className="text-text-primary font-semibold">{instanceDelta}</span>
          </div>
          {recommendation.urgency && (
            <div className="text-xs text-text-secondary">
              Urgency: <span className="text-text-primary font-semibold capitalize">{recommendation.urgency}</span>
            </div>
          )}
        </div>
      </Card>

      <DecisionLogDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  );
}
