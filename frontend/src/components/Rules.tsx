import { AppShell } from "./layout";
import { useEffect, useState } from "react";
import { api, type ApiRule, type CreateRule } from "../api/client";
import { HugeiconsIcon } from "@hugeicons/react";
import { Cancel01Icon, MoreVerticalIcon, PlusSignIcon } from "@hugeicons/core-free-icons";

const emptyRule = (): CreateRule => ({ name: "", description: "" });

export function Rules() {
  const [rules, setRules] = useState<ApiRule[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [drafts, setDrafts] = useState<CreateRule[]>([emptyRule()]);
  const [isSaving, setIsSaving] = useState(false);
  const [openRuleId, setOpenRuleId] = useState<string | null>(null);
  const [removingRuleId, setRemovingRuleId] = useState<string | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.listRules().then(setRules);
  }, []);

  const updateDraft = (index: number, field: keyof CreateRule, value: string) => {
    setDrafts((current) => current.map((rule, ruleIndex) => (ruleIndex === index ? { ...rule, [field]: value } : rule)));
  };

  const openDialog = () => {
    setError("");
    setDrafts([emptyRule()]);
    setIsDialogOpen(true);
  };

  const closeDialog = () => {
    if (!isSaving) setIsDialogOpen(false);
  };

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const rulesToCreate = drafts.map((rule) => ({ name: rule.name.trim(), description: rule.description.trim() })).filter((rule) => rule.name && rule.description);
    if (rulesToCreate.length !== drafts.length) {
      setError("Every rule needs a name and description.");
      return;
    }
    setIsSaving(true);
    setError("");
    try {
      const created = await api.createRules(rulesToCreate);
      setRules((current) => [...current, ...created]);
      setIsDialogOpen(false);
    } catch {
      setError("Could not create the rules. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const removeRule = async (rule: ApiRule) => {
    if (!window.confirm(`Remove the rule “${rule.name}”?`)) return;
    setRemovingRuleId(rule.id);
    setOpenRuleId(null);
    setError("");
    try {
      await api.deleteRule(rule.id);
      setRules((current) => current.filter((currentRule) => currentRule.id !== rule.id));
    } catch {
      setError("Could not remove the rule. Please try again.");
    } finally {
      setRemovingRuleId(null);
    }
  };

  return (
    <AppShell>
      <div className="simple-intro">
        <div>
          <div className="eyebrow">POLICY ENGINE</div>
          <h1>Rules</h1>
          <p>Configure the checks that keep every transaction within policy.</p>
        </div>
        <button className="primary flex gap-1 items-center" onClick={openDialog}>
          <HugeiconsIcon icon={PlusSignIcon} size={14} className="mb-0.5" />
          New rule
        </button>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rule</th>
              <th>Condition</th>
              <th>Applied to</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => (
              <tr key={rule.id}>
                <td>
                  <strong>{rule.name}</strong>
                  <small>{rule.description}</small>
                </td>
                <td>Configured in backend</td>
                <td>Active workflows</td>
                <td className="relative text-right">
                  <button
                    type="button"
                    className="icon-btn"
                    aria-label={`Actions for ${rule.name}`}
                    aria-expanded={openRuleId === rule.id}
                    onClick={() => setOpenRuleId((current) => (current === rule.id ? null : rule.id))}
                    disabled={removingRuleId === rule.id}
                  >
                    <HugeiconsIcon icon={MoreVerticalIcon} size={16} />
                  </button>
                  {openRuleId === rule.id && (
                    <div className="absolute right-3 top-12 z-10 min-w-36 rounded-lg border border-line bg-white p-1 text-left shadow-lg">
                      <button type="button" className="w-full rounded-md px-3 py-2 text-left text-xs text-red-700 hover:bg-red-50" onClick={() => void removeRule(rule)}>
                        Remove Rule
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {isDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-5" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && closeDialog()}>
          <form className="w-full max-w-2xl rounded-xl border border-line bg-white p-6 shadow-2xl" onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="new-rule-title">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h2 id="new-rule-title" className="m-0 text-xl font-bold">
                  Create rules
                </h2>
                <p className="mt-1 text-sm text-muted">Add one or more checks to apply to future workflows.</p>
              </div>
              <button type="button" className="icon-btn" onClick={closeDialog} aria-label="Close dialog">
                <HugeiconsIcon icon={Cancel01Icon} size={16} />
              </button>
            </div>
            <div className="grid gap-3">
              {drafts.map((rule, index) => (
                <div className="rounded-lg border border-line bg-[#fafaf7] p-4" key={index}>
                  <div className="mb-3 flex items-center justify-between">
                    <strong className="text-xs uppercase tracking-widest text-muted">Rule {index + 1}</strong>
                    {drafts.length > 1 && (
                      <button type="button" className="text-xs text-muted underline" onClick={() => setDrafts((current) => current.filter((_, ruleIndex) => ruleIndex !== index))}>
                        Remove
                      </button>
                    )}
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="grid gap-1 text-xs font-semibold">
                      Name
                      <input
                        required
                        className="rounded-md border border-line bg-white px-3 py-2 text-sm font-normal outline-none focus:border-ink"
                        value={rule.name}
                        onChange={(event) => updateDraft(index, "name", event.target.value)}
                        placeholder="Maximum invoice amount"
                        autoFocus={index === 0}
                      />
                    </label>
                    <label className="grid gap-1 text-xs font-semibold">
                      Description
                      <input
                        required
                        className="rounded-md border border-line bg-white px-3 py-2 text-sm font-normal outline-none focus:border-ink"
                        value={rule.description}
                        onChange={(event) => updateDraft(index, "description", event.target.value)}
                        placeholder="Invoice total must not exceed $10,000."
                      />
                    </label>
                  </div>
                </div>
              ))}
            </div>
            {error && (
              <p className="mt-3 text-sm text-red-700" role="alert">
                {error}
              </p>
            )}
            <div className="mt-5 flex items-center justify-between gap-3">
              <button type="button" className="secondary flex gap-1 items-center" onClick={() => setDrafts((current) => [...current, emptyRule()])}>
                <HugeiconsIcon icon={PlusSignIcon} size={14} className="mb-0.5" />
                Add another rule
              </button>
              <div className="flex gap-2">
                <button type="button" className="secondary" onClick={closeDialog}>
                  Cancel
                </button>
                <button type="submit" className="primary" disabled={isSaving}>
                  {isSaving ? "Creating…" : "Create rules"}
                </button>
              </div>
            </div>
          </form>
        </div>
      )}
    </AppShell>
  );
}
