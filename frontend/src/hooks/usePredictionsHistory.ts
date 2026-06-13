import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';

export function usePredictionsHistory(region: string, limit: number = 100) {
  return useQuery({
    queryKey: ['predictions-history', region, limit],
    queryFn: async () => {
      const { data } = await api.get('/predictions/history', { params: { region, limit } });
      return data;
    },
    refetchInterval: 60000,
    retry: 2,
  });
}
