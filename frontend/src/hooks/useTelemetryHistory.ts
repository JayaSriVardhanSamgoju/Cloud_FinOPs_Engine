import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';

export function useTelemetryHistory(region: string, hours: number = 24) {
  return useQuery({
    queryKey: ['telemetry-history', region, hours],
    queryFn: async () => {
      const { data } = await api.get('/telemetry/history', { params: { region, hours } });
      return data;
    },
    refetchInterval: 60000,
    retry: 2,
  });
}
