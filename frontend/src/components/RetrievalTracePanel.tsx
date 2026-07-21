import type { RetrievalTraceEntry } from "@/lib/types";

export default function RetrievalTracePanel({ trace }: { trace: RetrievalTraceEntry[] }) {
  if (trace.length === 0) return null;

  return (
    <details className="rounded-md border border-black/10 dark:border-white/10">
      <summary className="cursor-pointer select-none px-3 py-2 text-xs font-semibold uppercase tracking-wide text-black/50 dark:text-white/50">
        Retrieval trace ({trace.length} chunks)
      </summary>
      <table className="w-full border-t border-black/10 dark:border-white/10 text-xs">
        <thead>
          <tr className="text-left text-black/40 dark:text-white/40">
            <th className="px-3 py-1.5 font-medium">Chunk</th>
            <th className="px-3 py-1.5 font-medium">Page</th>
            <th className="px-3 py-1.5 font-medium">Method</th>
            <th className="px-3 py-1.5 font-medium">Distance</th>
          </tr>
        </thead>
        <tbody>
          {trace.map((entry) => (
            <tr key={entry.chunk_id} className="border-t border-black/5 dark:border-white/5">
              <td className="px-3 py-1.5 font-mono">{entry.chunk_id}</td>
              <td className="px-3 py-1.5">{String(entry.page)}</td>
              <td className="px-3 py-1.5">{entry.retrieval_method}</td>
              <td className="px-3 py-1.5">{entry.score !== null ? entry.score.toFixed(3) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}
