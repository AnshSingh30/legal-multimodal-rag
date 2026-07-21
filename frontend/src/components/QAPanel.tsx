"use client";

import { useState } from "react";
import { ApiError, queryDocument } from "@/lib/api";
import { stripCitationTags } from "@/lib/format";
import type { QueryResponse } from "@/lib/types";
import ConfidenceBadge from "./ConfidenceBadge";
import CitationList from "./CitationList";

type Status = "idle" | "asking" | "done" | "error";

export default function QAPanel({
  docId,
  onResult,
}: {
  docId: string | null;
  onResult?: (result: QueryResponse) => void;
}) {
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);

  const handleAsk = async () => {
    if (!question.trim() || status === "asking") return;
    setStatus("asking");
    setError(null);
    try {
      const response = await queryDocument({ question, doc_id: docId });
      setResult(response);
      setStatus("done");
      onResult?.(response);
    } catch (err) {
      setStatus("error");
      setError(err instanceof ApiError ? err.message : "Failed to get an answer.");
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleAsk();
          }}
          disabled={!docId || status === "asking"}
          placeholder={docId ? "Ask a question about your document…" : "Upload a document first"}
          className="flex-1 rounded-md border border-black/15 dark:border-white/15 bg-transparent px-3 py-2 text-sm disabled:opacity-50"
        />
        <button
          onClick={handleAsk}
          disabled={!docId || status === "asking" || !question.trim()}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {status === "asking" ? "Thinking…" : "Ask"}
        </button>
      </div>

      {status === "asking" && (
        <p className="text-sm text-black/50 dark:text-white/50">
          Retrieving context and generating a grounded answer — this can take a little while.
        </p>
      )}

      {status === "error" && error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      {status === "done" && result && (
        <div className="flex flex-col gap-3 rounded-lg border border-black/10 dark:border-white/10 p-4">
          <ConfidenceBadge confidence={result.confidence} />
          <p className="whitespace-pre-wrap text-sm">{stripCitationTags(result.answer)}</p>
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-black/50 dark:text-white/50">
              Citations
            </h3>
            <CitationList citations={result.citations} />
          </div>
        </div>
      )}
    </div>
  );
}
