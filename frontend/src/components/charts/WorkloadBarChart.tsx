import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';
import { Card } from '@/components/ui/Card';
import { chartColors } from '@/lib/colors';

interface WorkloadBarChartProps {
  data: Array<{
    workload_type: string;
    avg_cpu: number;
    avg_request_rate: number;
    avg_latency: number;
    avg_disk_io: number;
  }>;
}

export function WorkloadBarChart({ data }: WorkloadBarChartProps) {
  return (
    <Card>
      <h3 className="text-sm font-semibold text-text-primary mb-4">Workload Comparison</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis type="number" stroke="#8B8D97" fontSize={10} tickLine={false} />
          <YAxis
            type="category"
            dataKey="workload_type"
            stroke="#8B8D97"
            fontSize={10}
            tickLine={false}
            width={120}
          />
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
          <Bar dataKey="avg_cpu" name="CPU" fill={chartColors[0]} radius={[0, 4, 4, 0]} />
          <Bar dataKey="avg_latency" name="Latency" fill={chartColors[2]} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
