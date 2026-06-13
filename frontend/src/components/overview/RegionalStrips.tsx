import { useRegionalSummary } from '@/hooks/useRegionalSummary';
import { useStore } from '@/store/useStore';
import { motion } from 'framer-motion';

export function RegionalStrips() {
  const { data } = useRegionalSummary();
  const regions = data?.regions || [];
  const { region, setRegion } = useStore();

  return (
    <div className="flex flex-col gap-3 h-full">
      {regions.slice(0, 3).map((r: any, i: number) => {
        const cpu = r.avg_cpu || 0;
        const isSelected = region === r.region || region === 'All';
        
        return (
          <motion.div 
            key={r.region}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            onClick={() => setRegion(r.region)}
            className={`p-3 bg-surface-2 rounded border cursor-pointer transition-colors ${isSelected ? 'border-border-hover' : 'border-border opacity-60 hover:opacity-100'}`}
          >
            <div className="flex justify-between items-end mb-2">
              <span className="font-mono text-xs text-text-primary uppercase tracking-widest">{r.region}</span>
              <span className="font-mono text-xs text-text-tertiary">{r.avg_request_rate?.toFixed(0) || 0} RPS</span>
            </div>
            <div className="h-1.5 w-full bg-surface-3 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all duration-1000 ${cpu > 80 ? 'bg-status-critical' : cpu > 60 ? 'bg-status-warning' : 'bg-status-healthy'}`} 
                style={{ width: `${cpu}%` }} 
              />
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
