import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { CommandPalette } from '@/components/layout/CommandPalette';
import { ToastContainer } from '@/components/layout/Toast';

// Temporarily import existing pages (will be rewritten next)
import { Overview } from '@/pages/Overview';
import { Predictions } from '@/pages/Predictions';
import { Regional } from '@/pages/Regional';
import { FinOps } from '@/pages/FinOps';
import { ModelHealth } from '@/pages/ModelHealth';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

function AnimatedRoutes() {
  const location = useLocation();
  
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<PageTransition><Overview /></PageTransition>} />
        <Route path="/predictions" element={<PageTransition><Predictions /></PageTransition>} />
        <Route path="/regional" element={<PageTransition><Regional /></PageTransition>} />
        <Route path="/finops" element={<PageTransition><FinOps /></PageTransition>} />
        <Route path="/model-health" element={<PageTransition><ModelHealth /></PageTransition>} />
      </Routes>
    </AnimatePresence>
  );
}

function PageTransition({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -8 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="h-full"
    >
      {children}
    </motion.div>
  );
}

function AppLayout() {
  return (
    <div className="flex h-screen w-full bg-background overflow-hidden relative">
      <Sidebar />
      <div className="flex-1 ml-[220px] flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6 bg-background relative">
          <AnimatedRoutes />
        </main>
      </div>
      <CommandPalette />
      <ToastContainer />
    </div>
  );
}

import { ErrorBoundary } from '@/components/ErrorBoundary';

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppLayout />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
