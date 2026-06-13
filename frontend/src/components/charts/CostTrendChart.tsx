import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card } from '@/components/ui/Card';

interface CostTrendChartProps {
  data: Array<{ timestamp: string; cost_per_hour: number }>;
}

export function CostTrendChart({ data }: CostTrendChartProps) {
  const chartData = data.map((d) => ({
    ...d,
    time: new Date(d.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', hour12: false,
    }),
  }));

  return (
    <Card>
      <h3 className="text-sm font-semibold text-text-primary mb-4">Infrastructure Cost Trend</h3>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00D68F" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#00D68F" stopOpacity={0} />
            </linearGradient>
          </defs>
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
            formatter={(value: number) => [`$${value.toFixed(2)}/hr`, 'Cost']}
          />
          <Area
            type="monotone"
            dataKey="cost_per_hour"
            stroke="#00D68F"
            strokeWidth={2}
            fill="url(#costGradient)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}
