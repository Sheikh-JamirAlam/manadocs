import { AppShell } from "./layout";
import { useEffect } from "react";
import { useNavigate } from "react-router";
import { type ApiConflict, type ApiFinding } from "../api/client";
import { useConflictStore } from "../stores/conflictStore";
import { useFindingStore } from "../stores/findingStore";
import { HugeiconsIcon } from "@hugeicons/react";
import { ArrowRight02Icon, BookXIcon, SecurityWarningIcon } from "@hugeicons/core-free-icons";
export function Queue({ kind }: { kind: "conflicts" | "findings" }) {
  const navigate = useNavigate();
  const isConflict = kind === "conflicts";
  const isFinding = kind === "findings";
  const conflicts = useConflictStore((state) => state.conflicts);
  const loadConflicts = useConflictStore((state) => state.loadConflicts);
  const findings = useFindingStore((state) => state.findings);
  const loadFindings = useFindingStore((state) => state.loadFindings);
  useEffect(() => {
    if (isConflict) {
      void loadConflicts();
    } else if (isFinding) {
      void loadFindings();
    }
  }, [isConflict, isFinding, loadConflicts, loadFindings]);
  const items = (isConflict ? conflicts : findings).toSorted((a, b) => Number(b.status === "pending") - Number(a.status === "pending"));
  return (
    <AppShell>
      <div className="simple-intro">
        <div>
          <div className="eyebrow">REVIEW WORKSPACE</div>
          <h1>{isConflict ? "Conflicts" : "Rule findings"}</h1>
          <p>
            {isConflict
              ? "Compare competing claims and decide which source becomes truth."
              : isFinding
                ? "Business rules surfaced these items for human review."
                : "Review pending decisions first, followed by decisions already resolved."}
          </p>
        </div>
        <div className="queue-total">
          <strong>{items.length}</strong>
          <span>{items.some((item) => item.status === "pending") ? "pending decisions" : "resolved decisions"}</span>
        </div>
      </div>
      <div className="queue-list">
        {items.map((item) => (
          <div className="queue-card" key={item.id}>
            <div className="queue-card-top">
              <span className={isFinding ? "rule-icon" : "conflict-icon"}>{isFinding ? <HugeiconsIcon icon={SecurityWarningIcon} size={16} /> : <HugeiconsIcon icon={BookXIcon} size={16} />}</span>
              <div>
                <strong>{isFinding ? item.description : item.description || "Conflicting extracted claims"}</strong>
                <small>{isFinding ? (item as ApiFinding).rule_id : (item as ApiConflict).field_name}</small>
              </div>
              <span className={item.status === "resolved" ? "status status-approved" : "status status-awaiting-approval"}>{item.status}</span>
              <small>{"age" in item ? String(item.age ?? "") : ""}</small>
            </div>
            {isConflict && (
              <div className="claims">
                <div>
                  <small>DOCUMENT A</small>
                  <strong>{JSON.stringify((item as ApiConflict).conflicting_sources?.[0].citation?.quote || "Source A")}</strong>
                  <span>
                    {(item as ApiConflict).conflicting_sources?.[0].document_id || "Source A"} · Page {JSON.stringify((item as ApiConflict).conflicting_sources?.[0].citation?.page_number)}
                  </span>
                </div>
                <div className="versus">VS</div>
                <div>
                  <small>DOCUMENT B</small>
                  <strong>{JSON.stringify((item as ApiConflict).conflicting_sources?.[1].citation?.quote || "Source B")}</strong>
                  <span>
                    {(item as ApiConflict).conflicting_sources?.[1].document_id || "Source B"} · Page {JSON.stringify((item as ApiConflict).conflicting_sources?.[1].citation?.page_number)}
                  </span>
                </div>
              </div>
            )}
            <div className="queue-actions">
              {item.status === "resolved" ? (
                <button className="secondary">View resolution</button>
              ) : (
                <button
                  className="primary flex gap-1 items-center"
                  onClick={() => {
                    if (isFinding) {
                      navigate(`/findings/${(item as ApiFinding).document_id}`);
                    } else {
                      const documentId = (item as ApiConflict).conflicting_sources?.[0]?.document_id;
                      if (documentId) navigate(`/conflicts/${documentId}`);
                    }
                  }}
                >
                  {isFinding ? "Review finding" : "Resolve conflict"}
                  <HugeiconsIcon icon={ArrowRight02Icon} size={16} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
