import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Brush
} from 'recharts';
import { Card } from '@/components/ui/Card';

interface CpuTrendChartProps {
  data: Array<{
    timestamp: string;
    cpu_usage: number;
    is_anomaly?: boolean;
  }>;
}

export function CpuTrendChart({ data }: CpuTrendChartProps) {
  const chartData = data.map((d) => ({
    ...d,
    time: new Date(d.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', hour12: false,
    }),
    anomaly: d.is_anomaly ? d.cpu_usage : null,
  }));

  return (
    <Card>
      <h3 className="text-sm font-semibold text-text-primary mb-4">CPU Usage Trend</h3>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6C63FF" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#6C63FF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="time"
            stroke="#8B8D97"
            fontSize={10}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            stroke="#8B8D97"
            fontSize={10}
            tickLine={false}
            domain={[0, 100]}
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
          <ReferenceLine y={80} stroke="#FF3D71" strokeDasharray="4 4" label={{
            value: 'Scale Threshold',
            position: 'right',
            fill: '#FF3D71',
            fontSize: 10,
          }} />
          <Area
            type="monotone"
            dataKey="cpu_usage"
            stroke="#6C63FF"
            strokeWidth={2}
            fill="url(#cpuGradient)"
            dot={false}
            activeDot={{ r: 4, fill: '#6C63FF' }}
          />
          {/* Anomaly markers */}
          <Area
            type="monotone"
            dataKey="anomaly"
            stroke="none"
            fill="none"
            dot={{ r: 3, fill: '#FF3D71', stroke: '#FF3D71' }}
            activeDot={{ r: 5, fill: '#FF3D71' }}
          />
          <Brush
            dataKey="time"
            height={20}
            stroke="#6C63FF"
            fill="#1A1D27"
            travellerWidth={8}
          />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}
