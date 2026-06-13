import { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';
import { Card } from '@/components/ui/Card';

interface PredictionAccuracyChartProps {
  data: Array<{
    timestamp: string;
    predicted_cpu: number | null;
    actual_cpu: number | null;
  }>;
}

export function PredictionAccuracyChart({ data }: PredictionAccuracyChartProps) {
  const [showActual, setShowActual] = useState(true);

  const chartData = data
    .filter((d) => d.timestamp)
    .map((d) => ({
      time: new Date(d.timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', hour12: false,
      }),
      predicted: d.predicted_cpu,
      actual: d.actual_cpu,
    }))
    .reverse();

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-primary">Prediction Accuracy</h3>
        <label className="flex items-center gap-2 cursor-pointer">
          <span className="text-xs text-text-secondary">Show Actual</span>
          <div
            onClick={() => setShowActual(!showActual)}
            className={`w-8 h-4 rounded-full transition-colors cursor-pointer ${
              showActual ? 'bg-accent' : 'bg-white/10'
            } relative`}
          >
            <div
              className={`w-3 h-3 bg-white rounded-full absolute top-0.5 transition-transform ${
                showActual ? 'translate-x-4' : 'translate-x-0.5'
              }`}
            />
          </div>
        </label>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="time" stroke="#8B8D97" fontSize={10} tickLine={false} interval="preserveStartEnd" />
          <YAxis stroke="#8B8D97" fontSize={10} tickLine={false} domain={[0, 100]} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1A1D27',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              fontSize: '12px',
              color: '#E4E6EB',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '11px', color: '#8B8D97' }} />
          <Line
            type="monotone"
            dataKey="predicted"
            name="Predicted CPU"
            stroke="#6C63FF"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#6C63FF' }}
          />
          {showActual && (
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual CPU"
              stroke="#00D68F"
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={false}
              activeDot={{ r: 4, fill: '#00D68F' }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
