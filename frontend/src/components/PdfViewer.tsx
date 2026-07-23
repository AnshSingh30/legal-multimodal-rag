"use client";

import { useEffect, useMemo, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import type { Citation } from "@/lib/types";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const RENDER_WIDTH = 600;

// OCR bboxes are pixel coordinates at the 300dpi render Tesseract ran against;
// native-text bboxes are already in PDF point space (72dpi), which is what
// react-pdf/pdf.js render at before any zoom scaling — see rag/ingestion.py.
const OCR_DPI = 300;
const PDF_POINT_DPI = 72;

function toPdfPointSpace(citation: Citation): [number, number, number, number] | null {
  if (!citation.bbox) return null;
  const [x0, y0, x1, y1] = citation.bbox;
  if (citation.method === "ocr") {
    const factor = PDF_POINT_DPI / OCR_DPI;
    return [x0 * factor, y0 * factor, x1 * factor, y1 * factor];
  }
  return [x0, y0, x1, y1];
}

export default function PdfViewer({ docId, citations }: { docId: string; citations: Citation[] }) {
  const [numPages, setNumPages] = useState(0);
  const [pageScales, setPageScales] = useState<Map<number, number>>(new Map());
  const fileUrl = `${API_BASE_URL}/documents/${docId}/file`;

  const citationsByPage = useMemo(() => {
    const map = new Map<number, Citation[]>();
    for (const citation of citations) {
      const page = Number(citation.page_number);
      if (!Number.isFinite(page)) continue;
      const existing = map.get(page) ?? [];
      existing.push(citation);
      map.set(page, existing);
    }
    return map;
  }, [citations]);

  useEffect(() => {
    const firstCitedPage = citations
      .map((c) => Number(c.page_number))
      .find((p) => Number.isFinite(p));
    if (firstCitedPage !== undefined) {
      document
        .getElementById(`pdf-page-${firstCitedPage}`)
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [citations]);

  return (
    <div className="h-full overflow-y-auto bg-black/5 dark:bg-white/5 p-4">
      <Document
        file={fileUrl}
        onLoadSuccess={({ numPages }) => setNumPages(numPages)}
        loading={<p className="text-sm text-black/50 dark:text-white/50">Loading PDF…</p>}
        error={
          <p className="text-sm text-red-600 dark:text-red-400">
            Could not load a PDF preview for this document.
          </p>
        }
      >
        {Array.from({ length: numPages }, (_, i) => i + 1).map((pageNumber) => {
          const scale = pageScales.get(pageNumber) ?? 1;
          return (
            <div
              key={pageNumber}
              id={`pdf-page-${pageNumber}`}
              className="relative mb-4 shadow-sm"
            >
              <Page
                pageNumber={pageNumber}
                width={RENDER_WIDTH}
                onLoadSuccess={(page) =>
                  setPageScales((prev) => new Map(prev).set(pageNumber, RENDER_WIDTH / page.originalWidth))
                }
              />
              {(citationsByPage.get(pageNumber) ?? []).map((citation, i) => {
                const bbox = toPdfPointSpace(citation);
                if (!bbox) return null;
                const [x0, y0, x1, y1] = bbox;
                return (
                  <div
                    key={i}
                    className="pointer-events-none absolute border-2 border-yellow-400 bg-yellow-300/30"
                    style={{
                      left: x0 * scale,
                      top: y0 * scale,
                      width: (x1 - x0) * scale,
                      height: (y1 - y0) * scale,
                    }}
                  />
                );
              })}
            </div>
          );
        })}
      </Document>
    </div>
  );
}
