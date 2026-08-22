import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { AppShell } from "./layout";
import { highlightCitation, mergeChunkText } from "./documentText";
import { api, type ApiDocument, type ApiDocumentChunk, type ApiFinding } from "../api/client";
import { HugeiconsIcon } from "@hugeicons/react";
import { ArrowRight02Icon } from "@hugeicons/core-free-icons";

type ReviewDocument = ApiDocument & { findings: ApiFinding[]; content?: ApiDocumentChunk[] };

export function ReviewDetail({ kind }: { kind: "finding" | "conflict" }) {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<ReviewDocument | null>(null);
  const [active, setActive] = useState(0);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadDocument = useCallback(() => {
    if (!documentId) return;
    void api
      .getDocument(documentId)
      .then((nextDoc) => setDoc(nextDoc as ReviewDocument))
      .catch(() => setError("Document could not be loaded."));
  }, [documentId]);

  useEffect(loadDocument, [loadDocument]);

  if (!doc) {
    return (
      <AppShell>
        <div className="simple-intro">
          <h1>{error || "Loading review…"}</h1>
        </div>
      </AppShell>
    );
  }

  const findings = doc.findings || [];
  const finding = findings[active];
  const content = mergeChunkText(doc.content || []);
  const resolve = (item: ApiFinding, decision: "accept" | "reject") => {
    if (submitting) return;
    setSubmitting(true);
    void api
      .resolveFinding(item.thread_id, item.id, decision)
      .then(() => navigate("/findings"))
      .catch(() => setError("The finding could not be resolved."))
      .finally(() => setSubmitting(false));
  };

  return (
    <AppShell>
      <div className="detail-top">
        <div>
          <Link to={kind === "finding" ? "/findings" : "/conflicts"} className="back flex items-center gap-1">
            <HugeiconsIcon icon={ArrowRight02Icon} size={14} className="rotate-180" />
            {kind === "finding" ? "Rule findings" : "Conflicts"}
          </Link>
          <h1>{doc.filename}</h1>
          <div className="detail-meta">
            <span className="file-icon">{doc.filename.split(".").pop()?.toUpperCase() || "FILE"}</span>
            {doc.document_type} <i /> {doc.thread_id || "No workflow thread"}
          </div>
        </div>
      </div>
      <div className="detail-layout">
        <article className="document-paper">
          <div className="paper-toolbar">
            <span>{doc.filename}</span>
            <span>Rule review</span>
          </div>
          <div className="paper-content">
            {content.length ? (
              content.map((section, index) => (
                <p className="whitespace-pre-wrap" key={index}>
                  {highlightCitation(section, finding?.citation?.quote ? String(finding.citation.quote) : undefined, doc.filename.toLowerCase().endsWith(".pdf"))}
                </p>
              ))
            ) : (
              <p className="muted">The backend has not extracted readable text from this document yet.</p>
            )}
          </div>
        </article>
        <aside className="facts-panel">
          <div className="panel-title">
            <div>
              <h2>{kind === "finding" ? "Findings" : "Conflicts"}</h2>
              <p>
                {findings.length} finding{findings.length === 1 ? "" : "s"} · exact citations
              </p>
            </div>
          </div>
          {findings.map((item, index) => (
            <div
              className={`fact-card ${active === index ? "active" : ""}`}
              onClick={() => setActive(index)}
              key={item.id}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => event.key === "Enter" && setActive(index)}
            >
              <div className="fact-head">
                <strong>{item.rule_id}</strong>
                <span>{item.status}</span>
              </div>
              <b>{item.description}</b>
              {Boolean(item.citation?.quote) && <p>“{String(item.citation?.quote)}”</p>}
              <small>
                ⌖ Page {String(item.citation?.page_number ?? "—")}
                {String(item.citation?.section_header ?? "") ? ` · ${String(item.citation?.section_header)}` : ""}
              </small>
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
                    Enforce Rule
                  </button>
                </div>
              )}
            </div>
          ))}
          {error && <p className="api-error">{error}</p>}
        </aside>
      </div>
    </AppShell>
  );
}
