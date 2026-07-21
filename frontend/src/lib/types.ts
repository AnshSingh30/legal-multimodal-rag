// Mirrors api/schemas.py exactly — keep in sync with the backend.

export interface IngestResponse {
  doc_id: string;
  filename: string;
  chunks_indexed: number;
  document_version: number;
}

export interface QueryRequest {
  question: string;
  doc_id?: string | null;
  document_version?: number | null;
}

export interface SourceDocument {
  source: string;
  page: unknown;
  chunk_text: string;
}

export interface Citation {
  doc_id: string;
  page_number: unknown;
  bbox: [number, number, number, number] | null;
  chunk_text: string;
  method: "text" | "ocr" | null;
}

export type Confidence = "high" | "medium" | "low";

export interface RetrievalTraceEntry {
  chunk_id: string;
  source: string;
  page: unknown;
  score: number | null;
  retrieval_method: string;
}

export interface QueryResponse {
  answer: string;
  confidence: Confidence;
  source_documents: SourceDocument[];
  citations: Citation[];
  retrieval_trace: RetrievalTraceEntry[];
  chart: Record<string, unknown> | null;
  chart_type: string | null;
  chart_reason: string | null;
}

export interface VersionInfo {
  document_version: number;
  filename: string;
  content_hash: string | null;
  date_ingested: string | null;
  chunk_count: number;
}

export interface DiffEntry {
  key: string;
  status: "added" | "removed" | "changed";
  from_text: string | null;
  to_text: string | null;
  diff: string[] | null;
}

export interface DiffResponse {
  doc_id: string;
  from_version: number;
  to_version: number;
  entries: DiffEntry[];
}
