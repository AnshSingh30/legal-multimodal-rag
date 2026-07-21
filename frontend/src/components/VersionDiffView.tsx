"use client";

import { useEffect, useState } from "react";
import { ApiError, fetchDiff } from "@/lib/api";
import type { DiffResponse, VersionInfo } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  added: "border-green-400 bg-green-50 dark:bg-green-950/30",
  removed: "border-red-400 bg-red-50 dark:bg-red-950/30",
  changed: "border-amber-400 bg-amber-50 dark:bg-amber-950/30",
};

export default function VersionDiffView({
  docId,
  versions,
}: {
  docId: string;
  versions: VersionInfo[];
}) {
  const sorted = [...versions].sort((a, b) => a.document_version - b.document_version);
  const [from, setFrom] = useState(sorted[0]?.document_version);
  const [to, setTo] = useState(sorted[sorted.length - 1]?.document_version);
  const [diff, setDiff] = useState<DiffResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (from === undefined || to === undefined) return;
    let cancelled = false;

    async function loadDiff() {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchDiff(docId, from!, to!);
        if (!cancelled) setDiff(result);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load diff.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadDiff();
    return () => {
      cancelled = true;
    };
  }, [docId, from, to]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-black/50 dark:text-white/50">From</span>
        <select
          value={from}
          onChange={(e) => setFrom(Number(e.target.value))}
          className="rounded-md border border-black/15 dark:border-white/15 bg-transparent px-2 py-1"
        >
          {sorted.map((v) => (
            <option key={v.document_version} value={v.document_version}>
              v{v.document_version}
            </option>
          ))}
        </select>
        <span className="text-black/50 dark:text-white/50">to</span>
        <select
          value={to}
          onChange={(e) => setTo(Number(e.target.value))}
          className="rounded-md border border-black/15 dark:border-white/15 bg-transparent px-2 py-1"
        >
          {sorted.map((v) => (
            <option key={v.document_version} value={v.document_version}>
              v{v.document_version}
            </option>
          ))}
        </select>
      </div>

      {loading && <p className="text-sm text-black/50 dark:text-white/50">Loading diff…</p>}
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      {diff && !loading && (
        <div className="flex flex-col gap-2">
          {diff.entries.length === 0 ? (
            <p className="text-sm text-black/40 dark:text-white/40">No differences between these versions.</p>
          ) : (
            diff.entries.map((entry, i) => (
              <div
                key={i}
                className={`rounded-md border p-3 text-xs ${STATUS_STYLES[entry.status]}`}
              >
                <div className="mb-1 font-semibold uppercase tracking-wide">
                  {entry.status} — {entry.key}
                </div>
                {entry.status === "changed" && entry.diff ? (
                  <pre className="overflow-x-auto whitespace-pre-wrap font-mono">
                    {entry.diff.join("\n")}
                  </pre>
                ) : (
                  <p className="whitespace-pre-wrap">{entry.to_text ?? entry.from_text}</p>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
