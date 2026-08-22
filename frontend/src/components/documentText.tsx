import type { ApiDocumentChunk } from "../api/client";

export function highlightCitation(text: string, quote: string | undefined, isPdf = false) {
  if (!quote?.trim()) return text;
  const normalizedQuote = quote.trim().toLocaleLowerCase();
  let start = text.toLocaleLowerCase().indexOf(normalizedQuote);
  let end = start + quote.trim().length;
  if (start < 0 && isPdf) {
    const normalize = (value: string) => value
      .replace(/\\n|\/n|\r?\n/g, " ")
      .replace(/\s+/g, " ")
      .toLocaleLowerCase();
    const normalizedText = normalize(text);
    const normalizedCitation = normalize(quote.trim());
    start = normalizedText.indexOf(normalizedCitation);
    if (start >= 0) {
      const originalIndexes: number[] = [];
      let normalizedIndex = 0;
      for (let index = 0; index < text.length; index += 1) {
        if (/\s/.test(text[index]) && index > 0 && /\s/.test(text[index - 1])) continue;
        originalIndexes[normalizedIndex] = index;
        normalizedIndex += 1;
      }
      const originalStart = originalIndexes[start];
      const originalEnd = originalIndexes[start + normalizedCitation.length - 1];
      start = originalStart;
      end = originalEnd === undefined ? start : originalEnd + 1;
    }
  }
  if (start < 0) return text;
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
