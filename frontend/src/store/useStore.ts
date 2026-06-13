import { create } from 'zustand';

interface AppState {
  region: string;
  setRegion: (region: string) => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
}

export const useStore = create<AppState>((set) => ({
  region: 'All', // 'All', 'us-east-1', 'eu-west-1', 'ap-south-1'
  setRegion: (region) => set({ region }),
  isSidebarOpen: false,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
}));
