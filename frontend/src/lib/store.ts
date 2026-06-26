import { create } from 'zustand';

export interface DemoUser {
  id: string;
  displayName: string;
  role: 'CITIZEN' | 'AUTHORITY' | 'ADMIN' | 'NGO';
  ward: string;
}

export const DEMO_USERS: DemoUser[] = [
  { id: 'cit_1', displayName: 'Rohan Sharma (Citizen)', role: 'CITIZEN', ward: 'Indiranagar' },
  { id: 'cit_3', displayName: 'Amit Patel (Elite Citizen)', role: 'CITIZEN', ward: 'Whitefield' },
  { id: 'auth_1', displayName: 'Officer K. Rao (Road Authority)', role: 'AUTHORITY', ward: 'Indiranagar' },
  { id: 'auth_2', displayName: 'Officer M. Gowda (Water Authority)', role: 'AUTHORITY', ward: 'Koramangala' },
  { id: 'ngo_1', displayName: 'Green Bangalore (NGO)', role: 'NGO', ward: 'Indiranagar' }
];

interface CivioState {
  currentUser: DemoUser;
  activeWard: string;
  mapMode: 'pins' | 'heatmap' | 'decay';
  selectedIssueId: string | null;
  activeCategoryFilter: string | null;
  activeStatusFilter: string | null;
  triageDraft: any | null;
  
  // Actions
  setCurrentUser: (user: DemoUser) => void;
  setActiveWard: (ward: string) => void;
  setMapMode: (mode: 'pins' | 'heatmap' | 'decay') => void;
  setSelectedIssueId: (id: string | null) => void;
  setActiveCategoryFilter: (category: string | null) => void;
  setActiveStatusFilter: (status: string | null) => void;
  setTriageDraft: (draft: any | null) => void;
}

export const useCivioStore = create<CivioState>((set) => ({
  currentUser: DEMO_USERS[0],
  activeWard: 'Indiranagar',
  mapMode: 'pins',
  selectedIssueId: null,
  activeCategoryFilter: null,
  activeStatusFilter: null,
  triageDraft: null,

  setCurrentUser: (user) => set({ currentUser: user, activeWard: user.ward }),
  setActiveWard: (ward) => set({ activeWard: ward }),
  setMapMode: (mode) => set({ mapMode: mode }),
  setSelectedIssueId: (id) => set({ selectedIssueId: id }),
  setActiveCategoryFilter: (category) => set({ activeCategoryFilter: category }),
  setActiveStatusFilter: (status) => set({ activeStatusFilter: status }),
  setTriageDraft: (draft) => set({ triageDraft: draft }),
}));
