"use client";

import { useState } from "react";
import UploadPanel from "@/components/UploadPanel";
import QAPanel from "@/components/QAPanel";
import type { IngestResponse } from "@/lib/types";

export default function Home() {
  const [ingested, setIngested] = useState<IngestResponse | null>(null);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black">
      <main className="mx-auto flex max-w-3xl flex-col gap-8 px-6 py-12">
        <header>
          <h1 className="text-2xl font-semibold">Legal Multi-Modal RAG</h1>
          <p className="text-sm text-black/50 dark:text-white/50">
            Upload a document, then ask questions with cited, confidence-scored answers.
          </p>
        </header>

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
          <QAPanel docId={ingested?.doc_id ?? null} />
        </section>
      </main>
    </div>
  );
}
