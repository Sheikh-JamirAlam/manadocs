import { AppShell } from "./layout";
import { useEffect, useState } from "react";
import { api, type ApiMasterDeliverable } from "../api/client";
import { HugeiconsIcon } from "@hugeicons/react";
import { Download01Icon } from "@hugeicons/core-free-icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Deliverables() {
  const [master, setMaster] = useState<ApiMasterDeliverable | null>(null);
  useEffect(() => {
    api
      .getMasterDeliverable()
      .then(setMaster)
      .catch(() => setMaster(null));
  }, []);
  const exportLatest = () => {
    const previousTitle = document.title;
    document.title = master?.title || "DocTask deliverable";
    window.print();
    window.setTimeout(() => {
      document.title = previousTitle;
    }, 1000);
  };
  return (
    <AppShell>
      <div className="simple-intro">
        <div>
          <div className="eyebrow">OUTPUT ARCHIVE</div>
          <h1>Deliverables</h1>
          <p>Versioned, consolidated documents generated from approved facts and decisions.</p>
        </div>
        <button className="primary flex items-center gap-2" onClick={exportLatest} disabled={!master}>
          Export latest
          <HugeiconsIcon icon={Download01Icon} size={16} />
        </button>
      </div>
      <div className="deliverable-layout">
        <article className="deliverable-paper">
          <div className="paper-toolbar">
            <span>{master?.filename || "MASTER DELIVERABLE"}</span>
            <span>Markdown</span>
          </div>
          <div className="paper-content">
            <div className="max-w-239.5 w-full prose prose-h1:text-4xl prose-h1:font-normal prose-h1:mb-0 prose-em:text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{master?.content || "The backend has not generated a deliverable yet."}</ReactMarkdown>
            </div>
          </div>
        </article>
      </div>
    </AppShell>
  );
}
