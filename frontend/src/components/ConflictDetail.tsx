import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { AppShell } from "./layout";
import { highlightCitation, mergeChunkText } from "./documentText";
import { api, type ApiConflict, type ApiDocument, type ApiDocumentChunk } from "../api/client";
import { HugeiconsIcon } from "@hugeicons/react";
import { ArrowRight02Icon } from "@hugeicons/core-free-icons";

type ConflictDocument = ApiDocument & { content?: ApiDocumentChunk[] };

export function ConflictDetail() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const [conflicts, setConflicts] = useState<ApiConflict[]>([]);
  const [activeConflictIndex, setActiveConflictIndex] = useState(0);
  const [documents, setDocuments] = useState<ConflictDocument[]>([]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadConflict = useCallback(() => {
    if (!documentId) return;
    void api
      .getDocument(documentId)
      .then(async (sourceDocument) => {
        const sourceConflicts = (sourceDocument.conflicts || []).filter((item) => item.conflicting_sources?.some((source) => source.document_id === documentId));
        if (!sourceConflicts.length) {
          throw new Error("Conflict could not be found.");
        }
        const sourceIds = sourceConflicts.flatMap((item) => item.conflicting_sources.map((source) => source.document_id));
        const uniqueIds = [...new Set(sourceIds.filter((id): id is string => Boolean(id)))];
        const loadedDocuments = await Promise.all(uniqueIds.map((id) => api.getDocument(id)));
        setConflicts(sourceConflicts);
        setDocuments(loadedDocuments as ConflictDocument[]);
      })
      .catch(() => setError("The conflict documents could not be loaded."));
  }, [documentId]);

  useEffect(loadConflict, [loadConflict]);

  const resolve = (item: ApiConflict, decision: "accept" | "reject") => {
    if (submitting) return;
    setSubmitting(true);
    void api
      .resolveConflict(item.thread_id, item.id, decision)
      .then(() => navigate("/conflicts"))
      .catch(() => setError("The conflict could not be resolved."))
      .finally(() => setSubmitting(false));
  };

  const activeConflict = conflicts[activeConflictIndex];

  if (!activeConflict || documents.length < 2) {
    return (
      <AppShell>
        <div className="simple-intro">
          <h1>{error || "Loading conflict…"}</h1>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="detail-top">
        <div>
          <Link to="/conflicts" className="back flex items-center gap-1">
            <HugeiconsIcon icon={ArrowRight02Icon} size={14} className="rotate-180" />
            Conflicts
          </Link>
          <h1>{activeConflict.description || activeConflict.field_name}</h1>
          <div className="detail-meta">
            {activeConflict.field_name} <i /> Compare source documents and citations
          </div>
        </div>
      </div>
      <div className="conflict-review-panel">
        <div className="panel-title">
          <div>
            <h2>Conflicts</h2>
            <p>
              {conflicts.length} conflict{conflicts.length === 1 ? "" : "s"} · exact citations
            </p>
          </div>
        </div>
        <div className="conflict-list">
          {conflicts.map((item, index) => (
            <div
              className={`fact-card ${activeConflictIndex === index ? "active" : ""}`}
              key={item.id}
              onClick={() => setActiveConflictIndex(index)}
              onKeyDown={(event) => event.key === "Enter" && setActiveConflictIndex(index)}
              role="button"
              tabIndex={0}
            >
              <div className="fact-head">
                <strong>{item.field_name}</strong>
                <span>{item.status}</span>
              </div>
              <b>{item.description || "Conflicting extracted claims"}</b>
              <small>{item.conflicting_sources.length} source citations</small>
              {item.status === "pending" && (
                <div className="queue-actions">
                  <button
                    className="secondary"
                    disabled={submitting}
                    onClick={(event) => {
                      event.stopPropagation();
                      resolve(item, "accept");
                    }}
                  >
                    Ignore
                  </button>
                  <button
                    className="primary"
                    disabled={submitting}
                    onClick={(event) => {
                      event.stopPropagation();
                      resolve(item, "reject");
                    }}
                  >
                    Flag conflict
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="conflict-document-grid">
        {documents.map((document, index) => {
          const source = activeConflict.conflicting_sources.find((item) => item.document_id === document.id);
          const citation = source?.citation;
          const content = mergeChunkText(document.content || []);
          return (
            <article className="document-paper" key={document.id}>
              <div className="paper-toolbar">
                <span>{document.filename}</span>
                <span>DOCUMENT {String.fromCharCode(65 + index)}</span>
              </div>
              <div className="paper-content">
                {content.length ? (
                  content.map((section, sectionIndex) => (
                    <p className="whitespace-pre-wrap" key={sectionIndex}>
                      {highlightCitation(section, citation?.quote ? String(citation.quote) : undefined)}
                    </p>
                  ))
                ) : (
                  <p className="muted">No readable text is available for this document.</p>
                )}
              </div>
            </article>
          );
        })}
      </div>
      {error && <p className="api-error">{error}</p>}
    </AppShell>
  );
}
