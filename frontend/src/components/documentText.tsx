import type { ApiDocumentChunk } from "../api/client";

export function highlightCitation(text: string, quote: string | undefined) {
  if (!quote?.trim()) return text;
  const normalizedQuote = quote.trim().toLocaleLowerCase();
  const start = text.toLocaleLowerCase().indexOf(normalizedQuote);
  if (start < 0) return text;
  const end = start + quote.trim().length;
  return (
    <>
      {text.slice(0, start)}
      <mark className="selected">{text.slice(start, end)}</mark>
      {text.slice(end)}
    </>
  );
}

export function mergeChunkText(chunks: ApiDocumentChunk[]) {
  return chunks.reduce<string[]>((merged, chunk, index) => {
    const cleaned = chunk.content.replace(/^\s*Page\s+\d+\s*$/gim, "").replace(/\n\s*Page\s+\d+\s*(?=\n|$)/gi, "");
    if (!cleaned.trim()) return merged;
    if (!merged.length) return [cleaned];
    const previousChunk = chunks[index - 1];
    const samePage = previousChunk?.metadata.page_start === chunk.metadata.page_start;
    const previousText = merged[merged.length - 1];
    if (!samePage) {
      merged.push(cleaned);
      return merged;
    }
    const maxOverlap = Math.min(previousText.length, cleaned.length, 200);
    let overlapLength = 0;
    for (let length = maxOverlap; length > 0; length--) {
      if (previousText.slice(-length) === cleaned.slice(0, length)) {
        overlapLength = length;
        break;
      }
    }
    merged[merged.length - 1] = `${previousText}${cleaned.slice(overlapLength)}`;
    return merged;
  }, []);
}
