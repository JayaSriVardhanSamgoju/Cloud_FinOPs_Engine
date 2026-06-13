import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card } from '@/components/ui/Card';
import { chartColors } from '@/lib/colors';

interface RegionalBarChartProps {
  data: Array<{
    region: string;
    avg_cpu: number;
    avg_cost: number;
    avg_request_rate: number;
    anomaly_count: number;
  }>;
  dataKey: string;
  title: string;
  color?: string;
}

export function RegionalBarChart({ data, dataKey, title, color = chartColors[0] }: RegionalBarChartProps) {
  return (
    <Card>
      <h3 className="text-sm font-semibold text-text-primary mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="region" stroke="#8B8D97" fontSize={10} tickLine={false} />
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
          <Bar dataKey={dataKey} fill={color} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
