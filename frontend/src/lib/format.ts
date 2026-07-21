// The backend embeds [Citation: doc_id=..., page=...] tags in the answer text
// so it can parse and validate them (see rag/generation.py's _CITATION_RE) —
// but a user reading the answer doesn't need to see that bookkeeping syntax;
// the same information renders as a proper citation list already.
const CITATION_TAG_RE = /\[Citation:[^\]]*\]/g;

export function stripCitationTags(answer: string): string {
  return answer.replace(CITATION_TAG_RE, "").replace(/[ \t]+\n/g, "\n").trim();
}
