import { createContext, useContext, useState, ReactNode } from 'react';

interface RegionContextType {
  region: string;
  setRegion: (region: string) => void;
  regions: string[];
}

const RegionContext = createContext<RegionContextType | undefined>(undefined);

const REGIONS = ['us-east-1', 'ap-south-1', 'eu-west-1'];

export function RegionProvider({ children }: { children: ReactNode }) {
  const [region, setRegion] = useState('us-east-1');

  return (
    <RegionContext.Provider value={{ region, setRegion, regions: REGIONS }}>
      {children}
    </RegionContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useRegion() {
  const context = useContext(RegionContext);
  if (!context) throw new Error('useRegion must be used within RegionProvider');
  return context;
}
