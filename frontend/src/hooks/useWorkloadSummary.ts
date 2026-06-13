import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';

export function useWorkloadSummary(region?: string) {
  return useQuery({
    queryKey: ['workload-summary', region],
    queryFn: async () => {
      const { data } = await api.get('/telemetry/workload-summary', {
        params: region ? { region } : {},
      });
      return data;
    },
    refetchInterval: 60000,
    retry: 2,
  });
}
