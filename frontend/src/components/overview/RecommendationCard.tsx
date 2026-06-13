import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { StatusPill } from '@/components/primitives/StatusPill';

export function RecommendationCard({ recommendation }: { recommendation: any }) {
  const [open, setOpen] = useState(false);

  const recType = recommendation?.recommendation || 'maintain';
  const urgency = recommendation?.urgency || 'healthy';
  const instancesAdded = recommendation?.instances_to_add || 0;
  const instancesRemoved = recommendation?.instances_to_remove || 0;
  const delta = instancesAdded > 0 ? `+${instancesAdded}` : instancesRemoved > 0 ? `-${instancesRemoved}` : '0';
  const reason = recommendation?.reason || 'Stable load predicted.';

  return (
    <div className="flex flex-col h-full justify-between">
      <div>
        <StatusPill status={urgency === 'critical' ? 'critical' : urgency === 'high' ? 'warning' : 'healthy'} label={urgency.toUpperCase()} />
        
        <div className="mt-6 flex items-baseline justify-between">
          <h2 className="text-data-md font-mono text-text-primary uppercase tracking-tight">{recType.replace('_', ' ')}</h2>
          {delta !== '0' && (
            <span className={`text-data-lg font-mono ${instancesAdded > 0 ? 'text-status-warning' : 'text-status-info'}`}>
              {delta}
            </span>
          )}
        </div>
        
        <p className="mt-3 text-sm font-sans text-text-secondary leading-relaxed">
          {reason}
        </p>
      </div>

      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Trigger asChild>
          <button className="self-end mt-4 text-[10px] font-mono text-pulse hover:text-pulse-dim uppercase tracking-widest transition-colors">
            View Log →
          </button>
        </Dialog.Trigger>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-background/80 z-50 animate-fade-in" />
          <Dialog.Content className="fixed right-0 top-0 h-full w-[400px] bg-surface-1 border-l border-border z-50 p-6 overflow-y-auto animate-slide-in">
            <h2 className="text-sm font-mono text-text-tertiary uppercase tracking-widest mb-6">Decision Log</h2>
            <div className="space-y-6 relative before:absolute before:inset-0 before:ml-[11px] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border before:to-transparent">
              {/* Placeholder for history - backend integration later */}
              <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                <div className="w-6 h-6 rounded-full bg-surface-2 border-2 border-pulse absolute left-0 md:left-1/2 -translate-x-1/2 z-10 flex items-center justify-center">
                  <div className="w-2 h-2 bg-pulse rounded-full animate-pulse-dot" />
                </div>
                <div className="w-[calc(100%-3rem)] md:w-[calc(50%-2rem)] bg-surface-2 p-4 rounded border border-border">
                  <time className="text-[10px] font-mono text-text-tertiary">Just now</time>
                  <p className="font-mono text-sm mt-1">{recType}</p>
                </div>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="absolute top-4 right-4 text-text-tertiary hover:text-text-primary">✕</button>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
