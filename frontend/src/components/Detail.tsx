import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { HugeiconsIcon } from "@hugeicons/react";
import { ArrowLeft02Icon } from "@hugeicons/core-free-icons";
import { AppShell } from "./layout";
import { api, type ApiDocument, type ApiDocumentChunk, type ApiFact, type ApiRelatedDocument } from "../api/client";
import { useWorkflowStream, type WorkflowEvent } from "../hooks/useWorkflowStream";
import { highlightCitation, mergeChunkText } from "./documentText";

type DetailDocument = ApiDocument & { facts?: ApiFact; content?: ApiDocumentChunk[]; related_documents?: ApiRelatedDocument[] };
const stages = [
  { label: "Extracting", nodes: ["analyze_and_extract"] },
  { label: "Matching", nodes: ["find_matching_documents"] },
  { label: "Conflict check", nodes: ["audit_document_conflicts"] },
  { label: "Rule check", nodes: ["check_against_rule"] },
  { label: "Deliverable", nodes: ["generate_deliverable"] },
];

export function Detail() {
  const { id } = useParams();
  const [doc, setDoc] = useState<DetailDocument | null>(null);
  const [error, setError] = useState("");
  const [active, setActive] = useState("f0");
  const loadDocument = useCallback(() => {
    if (id)
      void api
        .getDocument(id)
        .then((nextDoc) => setDoc(nextDoc as DetailDocument))
        .catch(() => setError("Document could not be loaded."));
  }, [id]);
  useEffect(loadDocument, [loadDocument]);
  const handleWorkflowEvent = useCallback(
    (event: WorkflowEvent) => {
      setDoc((current) => (current ? { ...current, current_node: event.node_name || current.current_node, status: event.details?.status || current.status } : current));
      loadDocument();
    },
    [loadDocument],
  );
  useWorkflowStream(doc?.thread_id, handleWorkflowEvent);
  if (!doc)
    return (
      <AppShell>
        <div className="simple-intro">
          <h1>{error || "Loading document…"}</h1>
        </div>
      </AppShell>
    );
  const facts = doc.facts?.facts?.facts || [];
  const content = mergeChunkText(doc.content || []);
  const activeFact = facts[Number(active.slice(1))];
  const currentStage = stages.findIndex((stage) => stage.nodes.includes(doc.current_node || ""));
  const fileType = doc.filename.split(".").pop()?.toUpperCase() || "FILE";
  return (
    <AppShell>
      <div className="detail-top">
        <div>
          <Link to="/" className="back flex items-center gap-1">
            <HugeiconsIcon icon={ArrowLeft02Icon} size={14} />
            Document library
          </Link>
          <h1>{doc.filename}</h1>
          <div className="detail-meta">
            <span className="file-icon">{fileType}</span> {doc.document_type} <i /> {doc.thread_id || "No workflow thread"} <i /> Uploaded {new Date(doc.created_at).toLocaleDateString()}
          </div>
        </div>
      </div>
      <div className="stage-track">
        {stages.map((stage, index) => {
          const done = doc.status === "completed" || (currentStage >= 0 && index < currentStage);
          return (
            <div className={(index === currentStage ? "current " : "") + (done ? "done" : "")} key={stage.label}>
              <span>{done ? "✓" : index + 1}</span>
              {stage.label}
            </div>
          );
        })}
      </div>
      <div className="detail-layout">
        <article className="document-paper">
          <div className="paper-toolbar">
            <span>{doc.filename}</span>
            <span>{content.length ? `${content.length} text sections` : "No extracted text"}</span>
          </div>
          <div className="paper-content">
            {content.length ? (
              content.map((section, index) => (
                <p className="whitespace-pre-wrap" key={index}>
                  {highlightCitation(section, activeFact?.citation?.quote, fileType === "PDF")}
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
              <h2>Extracted facts</h2>
              <p>{facts.length} facts · 1 document</p>
            </div>
          </div>
          {facts.map((fact, index) => (
            <button className={"fact-card " + (active === `f${index}` ? "active" : "")} onClick={() => setActive(`f${index}`)} key={`${fact.field_name}-${index}`}>
              <div className="fact-head">
                <strong>{fact.field_name}</strong>
                <span>{fact.category}</span>
              </div>
              <b>{fact.description}</b>
              {fact.citation?.quote && <p>“{fact.citation.quote}”</p>}
              <small>
                ⌖ Page {fact.citation?.page_number || "—"}
                {fact.citation?.section_header ? ` · ${fact.citation.section_header}` : ""}
              </small>
            </button>
          ))}
        </aside>
      </div>
    </AppShell>
  );
}
