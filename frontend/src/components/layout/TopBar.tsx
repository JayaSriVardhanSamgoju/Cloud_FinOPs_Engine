import { useEffect, useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { LiveIndicator } from '@/components/primitives/LiveIndicator';
import { useStore } from '@/store/useStore';

export function TopBar() {
  const { region, setRegion } = useStore();
  const [time, setTime] = useState<string>('');

  // Client-side clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(
        now.toISOString().substring(11, 19) + ' UTC'
      );
    };
    updateTime();
    const int = setInterval(updateTime, 1000);
    return () => clearInterval(int);
  }, []);

  return (
    <header className="sticky top-0 h-16 bg-surface-0 border-b border-border z-20 flex items-center justify-between px-6">
      {/* Breadcrumb Title Placeholder - handled via routing if needed, but keeping it simple for now */}
      <div>
        <h2 className="text-data-md font-sans font-medium text-text-primary tracking-tight">
          Infrastructure Overview
        </h2>
      </div>

      <div className="flex items-center gap-6 h-full">
        <LiveIndicator />
        
        <div className="h-4 w-px bg-border" />
        
        <div className="font-mono text-sm text-text-secondary w-28 text-center">
          {time}
        </div>
        
        <div className="h-4 w-px bg-border" />

        <Tabs.Root value={region} onValueChange={setRegion} className="flex h-full items-center">
          <Tabs.List className="flex gap-1 bg-surface-1 p-1 rounded border border-border">
            {['All', 'us-east-1', 'eu-west-1', 'ap-south-1'].map((r) => (
              <Tabs.Trigger
                key={r}
                value={r}
                className="px-3 py-1 text-xs font-mono rounded text-text-secondary hover:text-text-primary data-[state=active]:bg-surface-2 data-[state=active]:text-pulse transition-all duration-200 border-b-2 border-transparent data-[state=active]:border-pulse"
              >
                {r.toUpperCase()}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
        </Tabs.Root>
      </div>
    </header>
  );
}
