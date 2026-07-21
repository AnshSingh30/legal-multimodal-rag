import type { Citation } from "@/lib/types";

export default function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) {
    return <p className="text-sm text-black/50 dark:text-white/50">No citations for this answer.</p>;
  }

  return (
    <ul className="space-y-2">
      {citations.map((citation, i) => (
        <li
          key={`${citation.doc_id}-${citation.page_number}-${i}`}
          className="rounded-md border border-black/10 dark:border-white/10 p-3 text-sm"
        >
          <div className="mb-1 font-medium text-black/70 dark:text-white/70">
            Page {String(citation.page_number)}
          </div>
          <p className="text-black/60 dark:text-white/60 line-clamp-3">{citation.chunk_text}</p>
        </li>
      ))}
    </ul>
  );
}
