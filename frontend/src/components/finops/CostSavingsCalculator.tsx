import { useState } from 'react';
import { Card } from '@/components/ui/Card';

export function CostSavingsCalculator() {
  const [reactiveDelay, setReactiveDelay] = useState(15);

  // Estimation logic:
  // Predictive scaling acts 30 min ahead. Reactive scaling acts AFTER threshold breach.
  // Each minute of delayed scaling during a spike costs ~$0.15 in wasted resources.
  // Assumption: ~3 spikes per day, each avoided by predictive scaling.
  const spikesPerDay = 3;
  const costPerMinuteWasted = 0.15;
  const dailySavings = spikesPerDay * reactiveDelay * costPerMinuteWasted;
  const monthlySavings = dailySavings * 30;

  return (
    <Card>
      <h3 className="text-sm font-semibold text-text-primary mb-4">
        💡 Cost Savings Calculator
      </h3>
      <p className="text-xs text-text-secondary mb-4">
        Estimate savings from predictive vs reactive autoscaling.
      </p>

      <div className="space-y-4">
        <div>
          <div className="flex justify-between text-xs mb-2">
            <span className="text-text-secondary">Reactive Scaling Lag</span>
            <span className="text-text-primary font-semibold">{reactiveDelay} min</span>
          </div>
          <input
            type="range"
            min={5}
            max={30}
            value={reactiveDelay}
            onChange={(e) => setReactiveDelay(Number(e.target.value))}
            className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer
              [&::-webkit-slider-thumb]:appearance-none
              [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
              [&::-webkit-slider-thumb]:bg-accent [&::-webkit-slider-thumb]:rounded-full
              [&::-webkit-slider-thumb]:cursor-pointer
              [&::-webkit-slider-thumb]:shadow-[0_0_8px_rgba(108,99,255,0.4)]"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-background rounded-[8px] p-3 border border-border text-center">
            <p className="text-xs text-text-secondary">Daily Savings</p>
            <p className="text-xl font-bold text-success mt-1">${dailySavings.toFixed(2)}</p>
          </div>
          <div className="bg-background rounded-[8px] p-3 border border-border text-center">
            <p className="text-xs text-text-secondary">Monthly Savings</p>
            <p className="text-xl font-bold text-success mt-1">${monthlySavings.toFixed(0)}</p>
          </div>
        </div>

        <div className="bg-accent/5 border border-accent/20 rounded-[8px] p-3">
          <p className="text-[10px] text-text-secondary leading-relaxed">
            <strong className="text-accent">Formula:</strong> {spikesPerDay} spikes/day × {reactiveDelay} min lag × ${costPerMinuteWasted}/min = ${dailySavings.toFixed(2)}/day.
            Predictive scaling eliminates the lag by forecasting CPU 30 minutes ahead.
          </p>
        </div>
      </div>
    </Card>
  );
}
