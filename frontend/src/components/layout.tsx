import { NavLink } from "react-router";
import { useEffect } from "react";
import { HugeiconsIcon } from "@hugeicons/react";
import { Archive02Icon, BookXIcon, Package02Icon, SecurityWarningIcon, ShieldEnergyIcon } from "@hugeicons/core-free-icons";
import { useConflictStore } from "../stores/conflictStore";
import { useFindingStore } from "../stores/findingStore";

export function AppShell({ children }: { children: React.ReactNode }) {
  const conflicts = useConflictStore((state) => state.conflicts);
  const loadConflicts = useConflictStore((state) => state.loadConflicts);

  useEffect(() => {
    void loadConflicts();
  }, [loadConflicts]);

  const pendingConflictCount = conflicts.filter((conflict) => conflict.status === "pending").length;
  const findings = useFindingStore((state) => state.findings);
  const loadFindings = useFindingStore((state) => state.loadFindings);

  useEffect(() => {
    void loadFindings();
  }, [loadFindings]);

  const pendingFindingCount = findings.filter((finding) => finding.status === "pending").length;

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 flex w-63 flex-col border-r border-line bg-[#f7f7f4]">
        <div className="px-4 pt-6.25">
          <div className="flex items-center gap-2.25 px-2.5 pb-6 text-[18px] font-extrabold">
            <span className="grid size-6.5 place-items-center rounded-[7px] bg-ink text-accent">D</span>
            <span>DocTask</span>
          </div>
        </div>
        <nav className="pt-0 px-4">
          <p>Review</p>
          <NavLink end to="/">
            <HugeiconsIcon icon={Archive02Icon} size={16} />
            <span>Document library</span>
          </NavLink>
          <NavLink to="/conflicts">
            <HugeiconsIcon icon={BookXIcon} size={16} />
            <span>Conflicts</span>
            <b className={`${pendingConflictCount > 0 ? "bg-amber-200 text-amber-800" : "bg-lime-300 text-lime-700"} count`}>{pendingConflictCount}</b>
          </NavLink>
          <NavLink to="/findings">
            <HugeiconsIcon icon={SecurityWarningIcon} size={16} />
            <span>Rule findings</span>
            <b className={`${pendingFindingCount > 0 ? "bg-amber-200 text-amber-800" : "bg-lime-300 text-lime-700"} count`}>{pendingFindingCount}</b>
          </NavLink>
          <p>Output</p>
          <NavLink to="/deliverables">
            <HugeiconsIcon icon={Package02Icon} size={16} />
            <span>Deliverables</span>
          </NavLink>
          <NavLink to="/rules">
            <HugeiconsIcon icon={ShieldEnergyIcon} size={16} />
            <span>Rules</span>
          </NavLink>
        </nav>
        <div className="user mt-auto py-4 px-3">
          <span className="avatar dark">JA</span>
          <div>
            <strong>Jamir Alam</strong>
            <small>Reviewer</small>
          </div>
          <span>⋮</span>
        </div>
      </aside>
      <main className="ml-63 w-[calc(100%-252px)] px-[5vw] pb-20">
        <header className="flex h-19.5 items-center justify-between border-b border-line">
          <div className="breadcrumbs">
            <span>DocTask</span>
            <span>/</span>
            <strong>Review workspace</strong>
          </div>
          <div className="header-actions">
            <div className="avatar dark">JA</div>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

export function StatusBadge({ value }: { value: string }) {
  return <span className={"status status-" + value.replaceAll(" ", "-")}>{value}</span>;
}
