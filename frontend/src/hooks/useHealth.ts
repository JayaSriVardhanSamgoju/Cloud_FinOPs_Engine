import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await api.get('/health');
      return data;
    },
    refetchInterval: 30000,
    retry: 2,
  });
}
