"use client";

import { useEffect, useState } from "react";
import { fetchVersions } from "@/lib/api";
import type { VersionInfo } from "@/lib/types";
import VersionDiffView from "./VersionDiffView";

export default function VersionPicker({
  docId,
  refreshKey,
  onVersionChange,
}: {
  docId: string;
  refreshKey: number;
  onVersionChange: (version: number | null) => void;
}) {
  const [versions, setVersions] = useState<VersionInfo[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [showDiff, setShowDiff] = useState(false);

  useEffect(() => {
    fetchVersions(docId)
      .then((v) => {
        setVersions(v);
        setSelected(null); // reset to "latest" whenever the document changes or a new version lands
      })
      .catch(() => setVersions([]));
  }, [docId, refreshKey]);

  if (versions.length <= 1) return null;

  const sorted = [...versions].sort((a, b) => b.document_version - a.document_version);
  const latest = sorted[0].document_version;

  return (
    <div className="flex flex-col gap-3 rounded-md border border-black/10 dark:border-white/10 p-3">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-black/50 dark:text-white/50">Query version:</span>
        <select
          value={selected ?? ""}
          onChange={(e) => {
            const value = e.target.value ? Number(e.target.value) : null;
            setSelected(value);
            onVersionChange(value);
          }}
          className="rounded-md border border-black/15 dark:border-white/15 bg-transparent px-2 py-1"
        >
          <option value="">Latest (v{latest})</option>
          {sorted.map((v) => (
            <option key={v.document_version} value={v.document_version}>
              v{v.document_version} ({v.chunk_count} chunks)
            </option>
          ))}
        </select>
        <button
          onClick={() => setShowDiff((s) => !s)}
          className="ml-auto text-xs text-blue-600 dark:text-blue-400 hover:underline"
        >
          {showDiff ? "Hide diff" : "View diff"}
        </button>
      </div>
      {showDiff && <VersionDiffView docId={docId} versions={versions} />}
    </div>
  );
}
