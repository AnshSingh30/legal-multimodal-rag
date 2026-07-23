"use client";

import { useCallback, useRef, useState } from "react";
import { ApiError, ingestDocument } from "@/lib/api";
import type { IngestResponse } from "@/lib/types";

const ACCEPTED_EXTENSIONS = [".pdf", ".csv", ".xlsx", ".xls", ".sql", ".docx"];

type Status = "idle" | "ingesting" | "done" | "error";

export default function UploadPanel({
  onIngested,
}: {
  onIngested: (result: IngestResponse) => void;
}) {
  const [status, setStatus] = useState<Status>("idle");
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ingested, setIngested] = useState<IngestResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      setStatus("error");
      setError(`Unsupported file type '${ext}'. Allowed: ${ACCEPTED_EXTENSIONS.join(", ")}`);
      return;
    }

    setStatus("ingesting");
    setError(null);
    try {
      const result = await ingestDocument(file);
      setIngested(result);
      setStatus("done");
      onIngested(result);
    } catch (err) {
      setStatus("error");
      setError(err instanceof ApiError ? err.message : "Failed to ingest document.");
    }
  }, [onIngested]);

  return (
    <div className="flex flex-col gap-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
        onClick={() => fileInputRef.current?.click()}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
          isDragOver
            ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
            : "border-black/20 dark:border-white/20 hover:border-black/40 dark:hover:border-white/40"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(",")}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        <p className="text-sm text-black/60 dark:text-white/60">
          Drag and drop a document here, or click to browse
        </p>
        <p className="mt-1 text-xs text-black/40 dark:text-white/40">
          PDF, CSV, Excel, SQL, or Word
        </p>
      </div>

      {status === "ingesting" && (
        <p className="text-sm text-blue-600 dark:text-blue-400">
          Ingesting document — for scanned/image-only PDFs this runs OCR and can take a while…
        </p>
      )}

      {status === "error" && error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      {status === "done" && ingested && (
        <div className="rounded-md bg-green-50 dark:bg-green-950/30 p-3 text-sm text-green-800 dark:text-green-300">
          Indexed <span className="font-medium">{ingested.filename}</span> (version{" "}
          {ingested.document_version}, {ingested.chunks_indexed} chunks).
        </div>
      )}
    </div>
  );
}
