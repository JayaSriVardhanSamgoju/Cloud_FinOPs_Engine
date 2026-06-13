import { useEffect, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useNavigate } from 'react-router-dom';
import { Search, Activity, Target, Globe, DollarSign, BrainCircuit } from 'lucide-react';
import { useStore } from '@/store/useStore';

const pages = [
  { path: '/', label: 'Overview', icon: Activity },
  { path: '/predictions', label: 'Predictions', icon: Target },
  { path: '/regional', label: 'Regional', icon: Globe },
  { path: '/finops', label: 'FinOps', icon: DollarSign },
  { path: '/model-health', label: 'Model Health', icon: BrainCircuit },
];

const regions = ['All', 'us-east-1', 'eu-west-1', 'ap-south-1'];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();
  const { setRegion } = useStore();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  const handleSelectPage = (path: string) => {
    navigate(path);
    setOpen(false);
    setSearch('');
  };

  const handleSelectRegion = (region: string) => {
    setRegion(region);
    setOpen(false);
    setSearch('');
  };

  const filteredPages = pages.filter(p => p.label.toLowerCase().includes(search.toLowerCase()));
  const filteredRegions = regions.filter(r => r.toLowerCase().includes(search.toLowerCase()));

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-background/80 z-50 animate-fade-in" />
        <Dialog.Content className="fixed left-1/2 top-[20%] -translate-x-1/2 w-full max-w-md bg-surface-1 border border-border rounded-lg shadow-2xl z-50 overflow-hidden animate-slide-up-fade">
          <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
            <Search className="w-4 h-4 text-text-secondary" />
            <input
              type="text"
              placeholder="Type a command or search..."
              className="flex-1 bg-transparent border-none outline-none text-sm font-sans text-text-primary placeholder:text-text-secondary"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>
          
          <div className="max-h-[300px] overflow-y-auto p-2">
            {filteredPages.length > 0 && (
              <div className="mb-4">
                <div className="px-2 py-1 text-[10px] font-mono text-text-tertiary uppercase tracking-wider">Pages</div>
                {filteredPages.map(page => (
                  <button
                    key={page.path}
                    onClick={() => handleSelectPage(page.path)}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded text-sm text-text-secondary hover:bg-surface-2 hover:text-text-primary hover:text-pulse transition-colors"
                  >
                    <page.icon className="w-4 h-4" />
                    {page.label}
                  </button>
                ))}
              </div>
            )}
            
            {filteredRegions.length > 0 && (
              <div>
                <div className="px-2 py-1 text-[10px] font-mono text-text-tertiary uppercase tracking-wider">Set Region</div>
                {filteredRegions.map(region => (
                  <button
                    key={region}
                    onClick={() => handleSelectRegion(region)}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded text-sm font-mono text-text-secondary hover:bg-surface-2 hover:text-pulse transition-colors"
                  >
                    <Globe className="w-4 h-4" />
                    {region}
                  </button>
                ))}
              </div>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
