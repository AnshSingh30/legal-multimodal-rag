"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import UploadPanel from "@/components/UploadPanel";
import QAPanel from "@/components/QAPanel";
import type { IngestResponse, QueryResponse } from "@/lib/types";

// react-pdf's pdf.js dependency references browser-only APIs (DOMMatrix) at
// module scope, which throws during Next.js's server-side render pass —
// ssr: false keeps that module out of the SSR bundle entirely.
const PdfViewer = dynamic(() => import("@/components/PdfViewer"), {
  ssr: false,
  loading: () => <p className="p-4 text-sm text-black/50 dark:text-white/50">Loading viewer…</p>,
});

export default function Home() {
  const [ingested, setIngested] = useState<IngestResponse | null>(null);
  const [lastResult, setLastResult] = useState<QueryResponse | null>(null);

  const isPdf = ingested?.filename.toLowerCase().endsWith(".pdf") ?? false;

  return (
    <div className="flex h-screen flex-col bg-zinc-50 dark:bg-black">
      <header className="border-b border-black/10 dark:border-white/10 px-6 py-4">
        <h1 className="text-2xl font-semibold">Legal Multi-Modal RAG</h1>
        <p className="text-sm text-black/50 dark:text-white/50">
          Upload a document, then ask questions with cited, confidence-scored answers.
        </p>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <div className="w-1/2 border-r border-black/10 dark:border-white/10">
          {ingested && isPdf ? (
            <PdfViewer docId={ingested.doc_id} citations={lastResult?.citations ?? []} />
          ) : (
            <div className="flex h-full items-center justify-center p-6 text-center text-sm text-black/40 dark:text-white/40">
              {ingested
                ? "PDF preview not available for this file type."
                : "Upload a PDF to see a citation-highlighted preview here."}
            </div>
          )}
        </div>

        <div className="flex w-1/2 flex-col gap-8 overflow-y-auto p-6">
          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-black/50 dark:text-white/50">
              1. Upload
            </h2>
            <UploadPanel onIngested={setIngested} />
          </section>

          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-black/50 dark:text-white/50">
              2. Ask
            </h2>
            <QAPanel docId={ingested?.doc_id ?? null} onResult={setLastResult} />
          </section>
        </div>
      </div>
    </div>
  );
}
