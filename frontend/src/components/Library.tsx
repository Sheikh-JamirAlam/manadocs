import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { HugeiconsIcon } from "@hugeicons/react";
import { ArrowRight01Icon, Tick01Icon } from "@hugeicons/core-free-icons";
import { AppShell } from "./layout";
import { Status } from "./Status";
import { api, type ApiDocument, type ApiLibrarySummary } from "../api/client";
import { useConflictStore } from "../stores/conflictStore";
import { useFindingStore } from "../stores/findingStore";
export function Library() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [type, setType] = useState("All types");
  const [documents, setDocuments] = useState<ApiDocument[]>([]);
  const [summary, setSummary] = useState<ApiLibrarySummary | null>(null);
  const [error, setError] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const refreshConflicts = useConflictStore((state) => state.refreshConflicts);
  const refreshFindings = useFindingStore((state) => state.refreshFindings);
  const uploadFiles = useCallback(async (files: FileList | File[]) => {
    const supportedFiles = Array.from(files).filter((file) => /\.(pdf|docx|txt)$/i.test(file.name));
    if (!supportedFiles.length) {
      setError("Please choose a PDF, DOCX, or TXT file.");
      return;
    }
    setError("");
    try {
      await Promise.all(supportedFiles.map((file) => api.upload(file)));
      const [nextDocuments, nextSummary] = await Promise.all([api.listDocuments(), api.getLibrarySummary()]);
      setDocuments(nextDocuments);
      setSummary(nextSummary);
    } catch {
      setError("Upload failed.");
    }
  }, []);
  const refreshLibrary = useCallback(() => {
    void Promise.all([api.listDocuments(), api.getLibrarySummary(), refreshConflicts(), refreshFindings()]).then(([nextDocuments, nextSummary]) => {
      setDocuments(nextDocuments);
      setSummary(nextSummary);
    });
  }, [refreshConflicts, refreshFindings]);
  useEffect(() => {
    Promise.all([api.listDocuments(), api.getLibrarySummary()])
      .then(([nextDocuments, nextSummary]) => {
        setDocuments(nextDocuments);
        setSummary(nextSummary);
      })
      .catch(() => setError("Backend unavailable. Start FastAPI to load documents."));
  }, []);
  const threadKey = useMemo(
    () =>
      documents
        .map((document) => document.thread_id)
        .filter((threadId): threadId is string => Boolean(threadId))
        .join("|"),
    [documents],
  );
  useEffect(() => {
    const globalSource = new EventSource(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/workflow/events/stream`);
    const handleGlobalEvent = () => refreshLibrary();
    globalSource.addEventListener("workflow", handleGlobalEvent);

    const sources = threadKey ? threadKey.split("|") : [];
    const handlers = new Map<string, EventSource>();
    sources.forEach((threadId) => {
      const source = new EventSource(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/workflow/${encodeURIComponent(threadId)}/events/stream`);
      const handleEvent = () => refreshLibrary();
      source.addEventListener("workflow", handleEvent);
      handlers.set(threadId, source);
    });
    return () => {
      globalSource.removeEventListener("workflow", handleGlobalEvent);
      globalSource.close();
      handlers.forEach((source) => source.close());
    };
  }, [threadKey, refreshLibrary]);
  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const normalizedType = type.toLowerCase();
    return documents.filter((d) => d.filename.toLowerCase().includes(normalizedQuery) && (type === "All types" || d.document_type === normalizedType));
  }, [documents, query, type]);
  const grid = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let cancelled = false;
    void import("gsap").then(({ default: gsap }) => {
      if (!cancelled && grid.current) {
        gsap.fromTo(grid.current.children, { y: 24, opacity: 0 }, { y: 0, opacity: 1, stagger: 0.07, duration: 0.6, ease: "power3.out" });
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return (
    <AppShell>
      <section className="page-intro">
        <div>
          <h1>
            Every document,
            <br />
            <em>decision-ready.</em>
          </h1>
          <p>Trace facts from source to deliverable. Resolve what needs your judgement, then let the workflow keep moving.</p>
        </div>
        <label className="primary">
          ＋ Upload documents
          <input
            ref={uploadInputRef}
            hidden
            type="file"
            multiple
            accept=".pdf,.docx,.txt"
            onChange={(e) => {
              if (e.target.files) void uploadFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </label>
      </section>
      <section className="metric-row">
        <div>
          <small>Documents in pipeline</small>
          <strong>{summary?.in_pipeline ?? "—"}</strong>
          <span>{summary ? `${summary.document_count} total documents` : "Loading…"}</span>
        </div>
        <div>
          <small>Needs your attention</small>
          <strong className="amber-text">{summary?.needs_attention ?? "—"}</strong>
          <span>{summary ? `${summary.pending_conflicts} conflicts · ${summary.pending_findings} findings` : "Loading…"}</span>
        </div>
        <div>
          <small>Processed this month</small>
          <strong>{summary?.processed_this_month ?? "—"}</strong>
          <span>{summary ? `${summary.transaction_count} transactions` : "Loading…"}</span>
        </div>
        <div className="metric-activity">
          <small>Latest activity {summary?.latest_activity && <span>· {new Date(summary.latest_activity.created_at).toLocaleString()}</span>}</small>
          {summary?.latest_activity ? (
            <p>
              <i className="activity-icon">
                <HugeiconsIcon icon={Tick01Icon} size={16} />
              </i>
              <span>
                <b>{summary.latest_activity.filename}</b> {summary.latest_activity.message || summary.latest_activity.event_type}
              </span>
            </p>
          ) : (
            <p>No workflow activity recorded yet.</p>
          )}
        </div>
      </section>
      <div className="section-heading">
        <div>
          <h2>Document library</h2>
          <p>
            {documents.length} documents · {summary?.transaction_count ?? "—"} transactions
          </p>
        </div>
        <div className="filters">
          <input placeholder="Search documents" value={query} onChange={(e) => setQuery(e.target.value)} />
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option>All types</option>
            <option>Contract</option>
            <option>Amendment</option>
            <option>Invoice</option>
            <option>Other</option>
          </select>
        </div>
      </div>
      <div className="workspace-grid" ref={grid}>
        <div
          className={`dropzone${isDragging ? " is-dragging" : ""}`}
          role="button"
          tabIndex={0}
          onClick={() => uploadInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") uploadInputRef.current?.click();
          }}
          onDragEnter={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragOver={(e) => e.preventDefault()}
          onDragLeave={(e) => {
            if (e.currentTarget === e.target) setIsDragging(false);
          }}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files.length) void uploadFiles(e.dataTransfer.files);
          }}
        >
          <strong>Drop documents here</strong>
          <span>PDF, DOCX, TXT up to 50 MB</span>
          <button className="secondary" type="button" onClick={(e) => {
            e.stopPropagation();
            uploadInputRef.current?.click();
          }}>Browse files</button>
        </div>
        <div className="mini-card dark-card">
          <small>ACTIVE TRANSACTION</small>
          <strong>{summary?.active_transaction?.thread_id?.slice(0, 8) || "No active transaction"}</strong>
          <p>{summary?.active_transaction ? `${summary.active_transaction.document_count} documents linked` : "Transactions appear after documents are matched."}</p>
        </div>
        <div className="mini-card accent-card">
          <small>WORKFLOW STATUS</small>
          <strong>{summary ? (summary.in_pipeline ? "In progress" : "Up to date") : "Loading…"}</strong>
          <p>{summary ? `${summary.in_pipeline} documents still moving through the pipeline` : "Loading workflow status…"}</p>
        </div>
      </div>
      {error && <p className="api-error">{error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Document</th>
              <th>Type</th>
              <th>Uploaded</th>
              <th>Transaction</th>
              <th>Current stage</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {filtered.map((d) => (
              <tr key={d.id} onClick={() => navigate("/documents/" + d.id)}>
                <td>
                  <span className="file-icon">{d.filename.split(".").pop()?.toUpperCase() || "FILE"}</span>
                  <div>
                    <strong>{d.filename}</strong>
                    <small>{Math.round(d.file_size_bytes / 1024)} KB</small>
                  </div>
                </td>
                <td>{d.document_type}</td>
                <td>{new Date(d.created_at).toLocaleDateString()}</td>
                <td>
                  <span className="transaction">{d.thread_id?.slice(0, 8) || "—"}</span>
                </td>
                <td>
                  <span className={`${d.status === "completed" ? "bg-lime-500" : "bg-amber"} stage-dot`} /> {d.current_node || d.status}
                </td>
                <td>
                  <Status value={d.status.replaceAll("_", " ")} />
                </td>
                <td>
                  <HugeiconsIcon icon={ArrowRight01Icon} size={16} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
