import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';

export function useRecommendationsHistory(limit: number = 20) {
  return useQuery({
    queryKey: ['recommendations-history', limit],
    queryFn: async () => {
      const { data } = await api.get('/recommendations/history', { params: { limit } });
      return data;
    },
    refetchInterval: 60000,
    retry: 2,
  });
}
