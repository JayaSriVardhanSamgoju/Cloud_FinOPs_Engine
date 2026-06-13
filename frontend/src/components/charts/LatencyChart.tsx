import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer
} from 'recharts';
import { Card } from '@/components/ui/Card';

interface LatencyChartProps {
  data: Array<{ timestamp: string; response_latency_ms: number }>;
}

export function LatencyChart({ data }: LatencyChartProps) {
  const chartData = data.map((d) => ({
    ...d,
    time: new Date(d.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', hour12: false,
    }),
  }));

  return (
    <Card>
      <h3 className="text-sm font-semibold text-text-primary mb-4">Response Latency</h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="time" stroke="#8B8D97" fontSize={10} tickLine={false} interval="preserveStartEnd" />
          <YAxis stroke="#8B8D97" fontSize={10} tickLine={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1A1D27',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              fontSize: '12px',
              color: '#E4E6EB',
            }}
          />
          <Line
            type="monotone"
            dataKey="response_latency_ms"
            stroke="#FFAA00"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#FFAA00' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
