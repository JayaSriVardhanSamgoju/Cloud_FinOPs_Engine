import { NavLink } from 'react-router-dom';
import { Activity, Target, Globe, DollarSign, BrainCircuit } from 'lucide-react';
import clsx from 'clsx';
import { useHealth } from '@/hooks/useHealth';
import { StatusPill } from '@/components/primitives/StatusPill';

const navItems = [
  { path: '/', label: 'Overview', icon: Activity },
  { path: '/predictions', label: 'Predictions', icon: Target },
  { path: '/regional', label: 'Regional', icon: Globe },
  { path: '/finops', label: 'FinOps', icon: DollarSign },
  { path: '/model-health', label: 'Model Health', icon: BrainCircuit },
];

function formatUptime(seconds: number) {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  return `${d}d ${h}h`;
}

export function Sidebar() {
  const { data: health } = useHealth();
  
  const status = health?.status === "operational" ? "healthy" : "critical";
  const uptime = health?.uptime_seconds ? formatUptime(health.uptime_seconds) : "0d 0h";

  return (
    <aside className="fixed left-0 top-0 h-full w-[220px] bg-surface-0 border-r border-border z-30 flex flex-col">
      {/* Logo */}
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 flex items-center justify-center text-pulse">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-full h-full">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>
              <path d="M2 12h20"/>
            </svg>
          </div>
          <div>
            <h1 className="text-xs font-mono font-bold text-text-primary tracking-[0.1em] uppercase">CloudPulse</h1>
            <p className="text-[9px] font-sans font-medium text-text-tertiary uppercase tracking-widest mt-0.5">AI Platform</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded text-[13px] font-sans font-medium transition-colors duration-150',
                isActive
                  ? 'bg-surface-1 border-l-2 border-pulse text-text-primary'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-1 border-l-2 border-transparent'
              )
            }
          >
            <item.icon className="w-4 h-4 opacity-70" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Footer System Status */}
      <div className="p-4 border-t border-border bg-surface-1/50">
        <h4 className="text-[10px] text-text-tertiary uppercase tracking-widest font-mono mb-3">System</h4>
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="text-text-secondary">Model</span>
            <span className="font-mono text-text-primary">{health?.model_version || 'v2.0'}</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-text-secondary">Uptime</span>
            <span className="font-mono text-text-primary">{uptime}</span>
          </div>
          <div className="pt-2">
            <StatusPill status={status} />
          </div>
        </div>
      </div>
    </aside>
  );
}
