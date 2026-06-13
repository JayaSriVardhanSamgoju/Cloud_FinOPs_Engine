import { useState, useEffect } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { useHealth } from '@/hooks/useHealth';
import { useRegion } from '@/context/RegionContext';

export function HeroHeader() {
  const [time, setTime] = useState(new Date());
  const { data: health } = useHealth();
  const { region, setRegion, regions } = useRegion();

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  const isOperational = health?.status === 'operational';

  return (
    <header className="bg-gradient-to-r from-card via-[#1E2235] to-card border-b border-border px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Left: Title + LIVE badge */}
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-text-primary tracking-tight">
            Predictive Infrastructure Intelligence
          </h1>
          <Badge variant="success" pulse size="md">
            LIVE
          </Badge>
        </div>

        {/* Right: Clock + Region + Status */}
        <div className="flex items-center gap-4">
          {/* Server Clock */}
          <div className="text-right">
            <p className="text-xs text-text-secondary">Server Time</p>
            <p className="text-sm font-mono text-text-primary tabular-nums">
              {time.toLocaleTimeString('en-US', { hour12: false })}
            </p>
          </div>

          {/* Region Selector */}
          <Select
            value={region}
            onChange={setRegion}
            options={regions.map((r) => ({ value: r, label: r }))}
          />

          {/* System Status */}
          <Badge variant={isOperational ? 'success' : 'danger'} size="md">
            {isOperational ? '● Operational' : '● Degraded'}
          </Badge>
        </div>
      </div>
    </header>
  );
}
