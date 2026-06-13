import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';

export function useModelInfo() {
  return useQuery({
    queryKey: ['model-info'],
    queryFn: async () => {
      const { data } = await api.get('/model/info');
      return data;
    },
    refetchInterval: 120000,
    retry: 2,
  });
}
