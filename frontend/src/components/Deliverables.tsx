import { AppShell } from "./layout";
import { useEffect, useState } from "react";
import { api, type ApiDeliverable } from "../api/client";
import { HugeiconsIcon } from "@hugeicons/react";
import { Download01Icon } from "@hugeicons/core-free-icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Deliverables() {
  const [items, setItems] = useState<ApiDeliverable[]>([]);
  useEffect(() => {
    api.listDeliverables().then(setItems);
  }, []);
  const current = items[0];
  const exportLatest = () => {
    const previousTitle = document.title;
    document.title = current?.title || "DocTask deliverable";
    window.print();
    window.setTimeout(() => { document.title = previousTitle; }, 1000);
  };
  return (
    <AppShell>
      <div className="simple-intro">
        <div>
          <div className="eyebrow">OUTPUT ARCHIVE</div>
          <h1>Deliverables</h1>
          <p>Versioned, consolidated documents generated from approved facts and decisions.</p>
        </div>
        <button className="primary flex items-center gap-2" onClick={exportLatest} disabled={!current}>
          Export latest
          <HugeiconsIcon icon={Download01Icon} size={16} />
        </button>
      </div>
      <div className="deliverable-layout">
        <article className="deliverable-paper">
          <div className="paper-toolbar">
            <span>{current?.title || "CONSOLIDATED SUMMARY"}</span>
            <span>v{current?.version || 0} · Markdown</span>
          </div>
          <div className="paper-content">
            <h2>{current?.title || "No deliverable available"}</h2>
            <p className="muted">Loaded from the DocTask API</p>
            <hr />
            <div className="deliverable-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {current?.content || "The backend has not generated a deliverable yet."}
              </ReactMarkdown>
            </div>
          </div>
        </article>
      </div>
    </AppShell>
  );
}
