import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/api/client';

export function useDriftStatus() {
  return useQuery({
    queryKey: ['drift-status'],
    queryFn: async () => {
      const { data } = await api.get('/drift/status');
      return data;
    },
    refetchInterval: 60000,
    retry: 2,
  });
}

export function useTriggerDrift() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/drift/run');
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['drift-status'] });
    },
  });
}
