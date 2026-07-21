import { stripCitationTags } from "@/lib/format";
import type { QueryResponse } from "@/lib/types";
import ConfidenceBadge from "./ConfidenceBadge";
import CitationList from "./CitationList";
import RetrievalTracePanel from "./RetrievalTracePanel";

export default function AnswerCard({
  question,
  result,
}: {
  question: string;
  result: QueryResponse;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-black/10 dark:border-white/10 p-4">
      <p className="text-xs font-medium text-black/40 dark:text-white/40">{question}</p>
      <ConfidenceBadge confidence={result.confidence} />
      <p className="whitespace-pre-wrap text-sm">{stripCitationTags(result.answer)}</p>
      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-black/50 dark:text-white/50">
          Citations
        </h3>
        <CitationList citations={result.citations} />
      </div>
      <RetrievalTracePanel trace={result.retrieval_trace} />
    </div>
  );
}
