"use client";

import { useQueryHistoryStore, type HistoryEntry } from "@/store/queryHistoryStore";
import ConfidenceBadge from "./ConfidenceBadge";

export default function QueryHistoryPanel({
  onSelect,
}: {
  onSelect: (entry: HistoryEntry) => void;
}) {
  const history = useQueryHistoryStore((s) => s.history);
  const clear = useQueryHistoryStore((s) => s.clear);

  if (history.length === 0) {
    return (
      <p className="text-sm text-black/40 dark:text-white/40">
        No queries yet this session.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <ul className="flex flex-col gap-1.5">
        {history.map((entry) => (
          <li key={entry.id}>
            <button
              onClick={() => onSelect(entry)}
              className="flex w-full items-center justify-between gap-2 rounded-md border border-black/10 dark:border-white/10 px-3 py-2 text-left text-sm hover:bg-black/5 dark:hover:bg-white/5"
            >
              <span className="truncate">{entry.question}</span>
              <ConfidenceBadge confidence={entry.result.confidence} />
            </button>
          </li>
        ))}
      </ul>
      <button
        onClick={clear}
        className="self-start text-xs text-black/40 dark:text-white/40 hover:underline"
      >
        Clear history
      </button>
    </div>
  );
}
