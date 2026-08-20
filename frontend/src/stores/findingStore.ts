import { create } from "zustand";
import { api, type ApiFinding } from "../api/client";

type FindingState = {
  findings: ApiFinding[];
  isLoading: boolean;
  error: string | null;
  hasLoaded: boolean;
  loadFindings: () => Promise<void>;
  refreshFindings: () => Promise<void>;
};

let findingsRequest: Promise<void> | null = null;

export const useFindingStore = create<FindingState>((set, get) => ({
  findings: [],
  isLoading: false,
  error: null,
  hasLoaded: false,
  loadFindings: async () => {
    if (get().hasLoaded) return;
    if (findingsRequest) return findingsRequest;

    set({ isLoading: true, error: null });
    findingsRequest = api.listFindings()
      .then((findings) => set({ findings, hasLoaded: true, isLoading: false }))
      .catch((error: unknown) => {
        set({ error: error instanceof Error ? error.message : "Unable to load rule findings", isLoading: false });
      })
      .finally(() => {
        findingsRequest = null;
      });

    return findingsRequest;
  },
  refreshFindings: async () => {
    if (findingsRequest) return findingsRequest;
    set({ isLoading: true, error: null });
    findingsRequest = api.listFindings()
      .then((findings) => set({ findings, hasLoaded: true, isLoading: false }))
      .catch((error: unknown) => {
        set({ error: error instanceof Error ? error.message : "Unable to load rule findings", isLoading: false });
      })
      .finally(() => {
        findingsRequest = null;
      });
    return findingsRequest;
  },
}));
