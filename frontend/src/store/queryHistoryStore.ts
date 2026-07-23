import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { QueryResponse } from "@/lib/types";

export interface HistoryEntry {
  id: string;
  question: string;
  docId: string | null;
  timestamp: number;
  result: QueryResponse;
}

interface QueryHistoryState {
  history: HistoryEntry[];
  addEntry: (question: string, docId: string | null, result: QueryResponse) => void;
  clear: () => void;
}

export const useQueryHistoryStore = create<QueryHistoryState>()(
  persist(
    (set) => ({
      history: [],
      addEntry: (question, docId, result) =>
        set((state) => ({
          history: [
            { id: crypto.randomUUID(), question, docId, timestamp: Date.now(), result },
            ...state.history,
          ],
        })),
      clear: () => set({ history: [] }),
    }),
    {
      name: "query-history",
      // sessionStorage, not localStorage: history should persist across
      // remounts/navigation within the tab's session, not survive closing it.
      storage: createJSONStorage(() => sessionStorage),
    },
  ),
);
