import { create } from "zustand";
import { api, type ApiConflict } from "../api/client";

type ConflictState = {
  conflicts: ApiConflict[];
  isLoading: boolean;
  error: string | null;
  hasLoaded: boolean;
  loadConflicts: () => Promise<void>;
  refreshConflicts: () => Promise<void>;
  removeConflict: (id: string) => void;
};

let conflictsRequest: Promise<void> | null = null;

export const useConflictStore = create<ConflictState>((set, get) => ({
  conflicts: [],
  isLoading: false,
  error: null,
  hasLoaded: false,
  loadConflicts: async () => {
    if (get().hasLoaded) return;
    if (conflictsRequest) return conflictsRequest;

    set({ isLoading: true, error: null });
    conflictsRequest = api.listConflicts()
      .then((conflicts) => set({ conflicts, hasLoaded: true, isLoading: false }))
      .catch((error: unknown) => {
        set({ error: error instanceof Error ? error.message : "Unable to load conflicts", isLoading: false });
      })
      .finally(() => {
        conflictsRequest = null;
      });

    return conflictsRequest;
  },
  refreshConflicts: async () => {
    if (conflictsRequest) return conflictsRequest;
    set({ isLoading: true, error: null });
    conflictsRequest = api.listConflicts()
      .then((conflicts) => set({ conflicts, hasLoaded: true, isLoading: false }))
      .catch((error: unknown) => {
        set({ error: error instanceof Error ? error.message : "Unable to load conflicts", isLoading: false });
      })
      .finally(() => {
        conflictsRequest = null;
      });
    return conflictsRequest;
  },
  removeConflict: (id) => set((state) => ({ conflicts: state.conflicts.filter((conflict) => conflict.id !== id) })),
}));
