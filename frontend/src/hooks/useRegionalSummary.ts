import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';

export function useRegionalSummary() {
  return useQuery({
    queryKey: ['regional-summary'],
    queryFn: async () => {
      const { data } = await api.get('/telemetry/regional-summary');
      return data;
    },
    refetchInterval: 60000,
    retry: 2,
  });
}
