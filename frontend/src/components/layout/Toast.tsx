import { create } from 'zustand';
import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

interface ToastState {
  toasts: Toast[];
  addToast: (message: string, type?: Toast['type']) => void;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  addToast: (message, type = 'info') => set((state) => {
    const id = Math.random().toString(36).substr(2, 9);
    return { toasts: [...state.toasts, { id, message, type }] };
  }),
  removeToast: (id) => set((state) => ({
    toasts: state.toasts.filter((t) => t.id !== id)
  })),
}));

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  useEffect(() => {
    const timers = toasts.map((t) => 
      setTimeout(() => removeToast(t.id), 4000)
    );
    return () => timers.forEach(clearTimeout);
  }, [toasts, removeToast]);

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className={`
              pointer-events-auto px-4 py-3 rounded border shadow-lg bg-surface-2 flex items-center gap-3
              ${toast.type === 'success' ? 'border-status-healthy/30 text-status-healthy' : ''}
              ${toast.type === 'error' ? 'border-status-critical/30 text-status-critical' : ''}
              ${toast.type === 'info' ? 'border-border text-text-primary' : ''}
            `}
          >
            {toast.type === 'success' && <span className="text-xl">✓</span>}
            {toast.type === 'error' && <span className="text-xl">!</span>}
            <span className="font-sans text-sm">{toast.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
