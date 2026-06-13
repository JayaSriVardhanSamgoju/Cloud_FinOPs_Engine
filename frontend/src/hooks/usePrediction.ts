import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';

export function usePrediction(region: string) {
  return useQuery({
    queryKey: ['prediction', region],
    queryFn: async () => {
      const { data } = await api.get('/predict', { params: { region } });
      return data;
    },
    refetchInterval: 30000,
    retry: 2,
  });
}
