import type { Confidence } from "@/lib/types";

const STYLES: Record<Confidence, string> = {
  high: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  medium: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  low: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
};

export default function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STYLES[confidence]}`}
    >
      {confidence} confidence
    </span>
  );
}
