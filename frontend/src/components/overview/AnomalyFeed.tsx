import { motion } from 'framer-motion';

export function AnomalyFeed({ history }: { history: any[] }) {
  const items = history?.filter(h => h.anomaly_score > 0.8) || [];

  return (
    <div className="max-h-[300px] overflow-y-auto pr-2 space-y-2">
      {items.length === 0 ? (
        <div className="text-sm font-mono text-text-secondary">SYSTEM NOMINAL. NO RECENT ANOMALIES.</div>
      ) : (
        items.map((item, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between p-3 rounded bg-surface-2 border border-border"
          >
            <div className="flex items-center gap-3">
              <span className="font-mono text-[10px] text-text-tertiary w-16">
                {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              <span className="text-xs font-mono text-status-warning bg-status-warning/10 px-1.5 py-0.5 rounded">
                {item.region}
              </span>
              <span className="text-sm font-sans text-text-primary">Spike Detected</span>
            </div>
            <div className="w-16 h-1.5 bg-surface-3 rounded-full overflow-hidden">
              <div className="h-full bg-status-critical" style={{ width: `${item.anomaly_score * 100}%` }} />
            </div>
          </motion.div>
        ))
      )}
    </div>
  );
}
