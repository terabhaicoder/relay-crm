"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { AutomationConditions, automationTriggers, conditionFields } from "@/components/automation-conditions";
import { Select } from "@/components/ui/select";
import { api, formatTimestamp, idempotencyRequest, type User } from "@/lib/api/client";
import type { Condition } from "@/lib/api/schema";
import styles from "./automation-workspace.module.css";

type Action = "create_task" | "notify" | "assign_owner";
type Step = { action: Action; action_text: string; delay_minutes: number; due_days: number; owner_id: string | null };
type Rule = { id: string; name: string; trigger: string; enabled: boolean; conditions: Condition[]; steps?: Step[]; action: Action; action_text: string; due_days: number };
type Job = { id: string; run_id: string; rule_id: string; rule_name: string; trigger?: string; step_index: number; action: Action; entity_type: string; entity_id: string; entity_name: string; status: "queued" | "completed" | "failed" | "cancelled" | "skipped"; scheduled_at: string | null; started_at: string | null; completed_at: string | null; result: string; result_entity_type: string | null; result_entity_id: string | null; error_detail: string | null; attempts: number };
type Run = { id: string; rule_name: string; entity_type: string; entity_id: string; entity_name: string; status: Job["status"]; created_at: string; completed_at: string | null; result: string };
type Page<T> = { items: T[]; total: number };
const pageSize = 12;
const actionNames: Record<Action, string> = { create_task: "Create a task", notify: "Notify a teammate", assign_owner: "Assign record owner" };
const eventNames: Record<string, string> = {
  "leads.created": "Lead created", "leads.updated": "Lead updated", "leads.converted": "Lead converted",
  "deals.created": "Deal created", "deals.won": "Deal won", "deals.lost": "Deal lost", "deals.stage_changed": "Deal stage changed",
  "tickets.created": "Ticket created", "tickets.updated": "Ticket updated", "activities.created": "Activity created", "activities.completed": "Activity completed",
};
const statusNames: Record<Job["status"], string> = { queued: "Scheduled", completed: "Completed", failed: "Failed", cancelled: "Cancelled", skipped: "Skipped" };
const newStep = (): Step => ({ action: "create_task", action_text: "", delay_minutes: 0, due_days: 1, owner_id: null });
const ruleSteps = (rule: Rule): Step[] => rule.steps?.length ? rule.steps : [{ ...newStep(), action: rule.action, action_text: rule.action_text, due_days: rule.due_days }];
const errorText = (error: unknown) => error instanceof Error ? error.message : "The request could not be completed. Please try again.";
function recordHref(entity: string, id: string): string | null {
  if (!["leads", "contacts", "parties", "deals", "activities", "tickets", "campaigns"].includes(entity) || !id) return null;
  return `/${entity === "parties" ? "accounts" : entity}?id=${encodeURIComponent(id)}`;
}

function useRemote<T>(path: string | null, revision: number) {
  const requestKey = `${path}:${revision}`;
  const [state, setState] = useState<{ key: string; data?: T; error?: string }>({ key: "" });
  useEffect(() => {
    if (path === null) return;
    const controller = new AbortController();
    api<T>(path, { signal: controller.signal }).then(data => setState({ key: requestKey, data })).catch(error => {
      if (!controller.signal.aborted) setState({ key: requestKey, error: errorText(error) });
    });
    return () => controller.abort();
  }, [path, requestKey]);
  return { data: state.key === requestKey ? state.data : undefined, error: state.key === requestKey ? state.error : undefined, loading: state.key !== requestKey };
}

function Pagination({ offset, total, onChange }: { offset: number; total: number; onChange: (offset: number) => void }) {
  return <div className={styles.pagination}>
    <span>{total === 0 ? "No results" : `${Math.min(offset + 1, total)}–${Math.min(offset + pageSize, total)} of ${total}`}</span>
    <button className="button secondary" type="button" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - pageSize))}>Previous</button>
    <button className="button secondary" type="button" disabled={offset + pageSize >= total} onClick={() => onChange(offset + pageSize)}>Next</button>
  </div>;
}

function RuleEditor({ rule, onClose, onSaved }: { rule: Rule | null; onClose: () => void; onSaved: (rule: Rule) => void }) {
  const [name, setName] = useState(rule?.name ?? "");
  const [trigger, setTrigger] = useState(rule?.trigger ?? "leads.created");
  const [enabled, setEnabled] = useState(rule?.enabled ?? true);
  const [conditions, setConditions] = useState<Condition[]>(rule?.conditions ?? []);
  const [steps, setSteps] = useState<Step[]>(rule ? ruleSteps(rule) : [newStep()]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [teamRevision, setTeamRevision] = useState(0);
  const team = useRemote<User[]>("/team", teamRevision);
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  const busyRef = useRef(false);
  const activeUsers = (team.data ?? []).filter(member => member.is_active !== false);
  const totalDelay = steps.reduce((sum, step) => sum + step.delay_minutes, 0);
  function updateStep(index: number, patch: Partial<Step>) { setSteps(previous => previous.map((step, position) => position === index ? { ...step, ...patch } : step)); }
  function moveStep(index: number, delta: number) {
    setSteps(previous => { const next = [...previous]; [next[index], next[index + delta]] = [next[index + delta]!, next[index]!]; return next; });
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busyRef.current) return;
    if (totalDelay > 43200) { setError("The combined delay must be 43,200 minutes (30 days) or less."); return; }
    if (steps.some(step => step.action === "assign_owner" && !step.owner_id)) { setError("Choose a teammate for every owner assignment."); return; }
    const legacy = steps.find(step => step.action !== "assign_owner");
    const body = { name: name.trim(), trigger, enabled, conditions, steps: steps.map(step => ({ ...step, action_text: step.action_text.trim() })), action: legacy?.action ?? "create_task", action_text: legacy?.action_text.trim() || name.trim(), due_days: legacy?.due_days ?? 1 };
    busyRef.current = true; setBusy(true); setError("");
    request.current = idempotencyRequest(body, request.current);
    try {
      const saved = await api<Rule>(rule ? `/automations/${rule.id}` : "/automations", { method: rule ? "PATCH" : "POST", headers: { "Idempotency-Key": request.current.key }, body: JSON.stringify(body) });
      onSaved(saved);
    } catch (failure) { setError(errorText(failure)); }
    finally { busyRef.current = false; setBusy(false); }
  }
  return <section className={styles.editor} aria-labelledby="automation-editor-title">
    <div className={styles.sectionHeader}><div><h3 id="automation-editor-title">{rule ? "Edit workflow" : "New workflow"}</h3><p>Choose an event, then set the work that should follow.</p></div><button type="button" className="button subtle" onClick={onClose} disabled={busy}>Close editor</button></div>
    <form onSubmit={save}>
      <fieldset disabled={busy} className={styles.fields}>
        <div className={styles.formGrid}>
          <label>Workflow name<input autoFocus required maxLength={200} value={name} onChange={event => setName(event.target.value)} placeholder="Follow up with new enquiries" /></label>
          <label>When this happens<Select value={trigger} onValueChange={value => { setTrigger(value); setConditions(previous => previous.filter(condition => conditionFields(value).includes(condition.field))); }}>{automationTriggers.map(value => <option key={value} value={value}>{eventNames[value]}</option>)}</Select></label>
        </div>
        <AutomationConditions value={conditions} onChange={setConditions} trigger={trigger} />
        <div className={styles.stepsHeading}><h4>Then, in this order</h4><p>Each delay starts after the previous step finishes. Conditions are checked again before every step.</p></div>
        {team.error && <div className={styles.error} role="alert">Teammates could not be loaded. {team.error} <button type="button" className="button secondary" onClick={() => setTeamRevision(value => value + 1)}>Reload teammates</button></div>}
        <ol className={styles.steps}>
          {steps.map((step, index) => <li key={index} className={styles.step}>
            <div className={styles.stepHeader}><h5>Step {index + 1}</h5><div className={styles.actions}>
              <button className="button subtle" type="button" aria-label={`Move step ${index + 1} up`} disabled={index === 0} onClick={() => moveStep(index, -1)}>Move up</button>
              <button className="button subtle" type="button" aria-label={`Move step ${index + 1} down`} disabled={index === steps.length - 1} onClick={() => moveStep(index, 1)}>Move down</button>
              <button className="button subtle" type="button" aria-label={`Remove step ${index + 1}`} disabled={steps.length === 1} onClick={() => setSteps(previous => previous.filter((_, position) => position !== index))}>Remove</button>
            </div></div>
            <div className={styles.formGrid}>
              <label>Action<Select aria-label={`Step ${index + 1} action`} value={step.action} onValueChange={action => updateStep(index, { action: action as Action })}>{Object.entries(actionNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select></label>
              <label>Delay in minutes<input aria-label={`Step ${index + 1} delay in minutes`} type="number" min={0} max={43200} step={1} required value={step.delay_minutes} onChange={event => updateStep(index, { delay_minutes: Number(event.target.value) })} /><small>{index === 0 ? "After the triggering event. Zero adds no delay." : "After the preceding step completes. Zero adds no delay."}</small></label>
              {step.action !== "assign_owner" && <label className={styles.wide}>{step.action === "create_task" ? "Task title" : "Notification message"}<input aria-label={`Step ${index + 1} ${step.action === "create_task" ? "task title" : "notification message"}`} required maxLength={500} value={step.action_text} onChange={event => updateStep(index, { action_text: event.target.value })} placeholder={step.action === "create_task" ? "Follow up with {{name}}" : "Please review {{name}}"} /><small>Use {"{{name}}"} for the triggering record’s name.{step.action === "notify" && " Notifications appear inside Relay."}</small></label>}
              <label>{step.action === "assign_owner" ? "New record owner" : step.action === "notify" ? "Notify" : "Assign task to"}<Select aria-label={`Step ${index + 1} teammate`} value={step.owner_id ?? ""} required={step.action === "assign_owner"} disabled={team.loading} onValueChange={value => updateStep(index, { owner_id: value || null })}>
                <option value="">{team.loading ? "Loading teammates…" : step.action === "assign_owner" ? "Choose a teammate" : "Current record owner"}</option>
                {step.owner_id && !activeUsers.some(member => member.id === step.owner_id) && <option value={step.owner_id} disabled>Unavailable teammate — choose another</option>}
                {activeUsers.map(member => <option key={member.id} value={member.id}>{member.name} · {member.email}</option>)}
              </Select>{step.action !== "assign_owner" && <small>If the record is unassigned, the workflow owner receives this step.</small>}</label>
              {step.action === "create_task" && <label>Task due after days<input aria-label={`Step ${index + 1} task due after days`} type="number" min={0} max={365} step={1} required value={step.due_days} onChange={event => updateStep(index, { due_days: Number(event.target.value) })} /><small>From when this step runs. Zero means the same day.</small></label>}
            </div>
          </li>)}
        </ol>
        <div className={styles.addStep}><button type="button" className="button secondary" disabled={steps.length >= 8} onClick={() => setSteps(previous => [...previous, newStep()])}>Add step</button><span>{steps.length} of 8 steps · {totalDelay.toLocaleString("en-IN")} minutes total delay</span></div>
        <label className={styles.checkbox}><input type="checkbox" checked={enabled} onChange={event => setEnabled(event.target.checked)} />Enable this workflow for new events</label>
        {rule && <p className={styles.note}>Changes apply to future events. Existing scheduled work keeps its saved steps. Pausing cancels pending work; enabling does not restore cancelled steps.</p>}
        {error && <div className={styles.error} role="alert">{error}</div>}
        <div className={styles.actions}><button className="button primary" type="submit" disabled={totalDelay > 43200}>{busy ? "Saving…" : rule ? "Save workflow" : "Create workflow"}</button><button className="button secondary" type="button" onClick={onClose}>Cancel</button></div>
      </fieldset>
    </form>
  </section>;
}

export function AutomationWorkspace({ user }: { user: User }) {
  const canManage = ["Owner", "Admin", "Sales Manager"].includes(user.role);
  const [tab, setTab] = useState<"rules" | "history">("rules");
  const [editor, setEditor] = useState<Rule | "new" | null>(null);
  const [revision, setRevision] = useState(0);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [ruleStatus, setRuleStatus] = useState("");
  const [ruleFilter, setRuleFilter] = useState<{ id: string; name: string } | null>(null);
  const [status, setStatus] = useState("");
  const [entity, setEntity] = useState("");
  const [historyOffset, setHistoryOffset] = useState(0);
  const [historySearch, setHistorySearch] = useState("");
  const [historyQuery, setHistoryQuery] = useState("");
  const [mutation, setMutation] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [confirm, setConfirm] = useState<{ type: "pause"; rule: Rule } | { type: "cancel"; job: Job } | null>(null);
  const mutationRef = useRef(false);
  const ruleParams = new URLSearchParams({ q: query, limit: String(pageSize), offset: String(offset), sort: "created_at", order: "desc" });
  if (ruleStatus) ruleParams.set("enabled", ruleStatus);
  const rules = useRemote<Page<Rule>>(`/automations?${ruleParams}`, revision);
  return <div className={styles.workspace}>
    <header className={styles.intro}><div><h2>Work that follows through</h2><p>Turn CRM events into assigned tasks, owner changes and in-app notifications.</p></div>{canManage && <button className="button primary" type="button" onClick={() => { setTab("rules"); setEditor("new"); setNotice(""); }}>New workflow</button>}</header>
    <nav className={styles.tabs} aria-label="Automation views"><button type="button" aria-current={tab === "rules" ? "page" : undefined} onClick={() => setTab("rules")}>Workflows</button><button type="button" aria-current={tab === "history" ? "page" : undefined} onClick={() => setTab("history")}>Execution history</button></nav>
    {notice && <p className={styles.success} role="status">{notice}</p>}
    {error && <div className={styles.error} role="alert">{error}</div>}
    {confirm && <div className={styles.confirm} role="alert"><div><strong>{confirm.type === "pause" ? `Pause “${confirm.rule.name}”?` : "Cancel this execution?"}</strong><p>{confirm.type === "pause" ? "Pending steps will be cancelled. Completed work is kept. Enabling later only handles new events." : "All pending steps in this execution will be cancelled. Completed work is kept."}</p></div><div className={styles.actions}><button className="button primary" type="button" disabled={!!mutation} onClick={() => { if (confirm.type === "pause") void toggleRule(confirm.rule); else void jobAction(confirm.job, "cancel"); }}>{mutation ? "Updating…" : confirm.type === "pause" ? "Pause workflow" : "Cancel execution"}</button><button className="button secondary" type="button" disabled={!!mutation} onClick={() => setConfirm(null)}>Keep running</button></div></div>}
    {tab === "rules" ? <>
      {editor !== null && <RuleEditor key={editor === "new" ? "new" : editor.id} rule={editor === "new" ? null : editor} onClose={() => setEditor(null)} onSaved={saved => { setEditor(null); setNotice(`“${saved.name}” saved${saved.enabled ? " and enabled" : " as paused"}.`); setRevision(value => value + 1); }} />}
      <form className={styles.filters} onSubmit={event => { event.preventDefault(); setQuery(search.trim()); setOffset(0); }}><label className={styles.search}>Search workflows<input type="search" maxLength={200} value={search} onChange={event => setSearch(event.target.value)} placeholder="Name or action text" /></label><label>Workflow status<Select value={ruleStatus} onValueChange={value => { setRuleStatus(value); setOffset(0); }}><option value="">All workflows</option><option value="true">Enabled</option><option value="false">Paused</option></Select></label><button className="button secondary" type="submit">Search</button><button className="button subtle" type="button" onClick={() => setRevision(value => value + 1)}>Refresh</button></form>
      {!canManage && <p className={styles.note}>You can review workflows and their history. Owners, admins and sales managers can configure them.</p>}
      <section className={styles.list} aria-label="Workflows" aria-busy={rules.loading}>
        {rules.error ? <div className={styles.error} role="alert">{rules.error}<button type="button" className="button secondary" onClick={() => setRevision(value => value + 1)}>Try again</button></div> : rules.loading ? <p className={styles.empty} role="status">Loading workflows…</p> : rules.data?.items.length ? rules.data.items.map(rule => <article className={styles.rule} key={rule.id}>
          <div className={styles.ruleTitle}><h3>{rule.name}</h3><span className={`${styles.status} ${rule.enabled ? styles.completed : styles.cancelled}`}>{rule.enabled ? "Enabled" : "Paused"}</span></div>
          <p className={styles.ruleMeta}>{eventNames[rule.trigger] ?? rule.trigger} · {rule.conditions.length ? `${rule.conditions.length} matching condition${rule.conditions.length === 1 ? "" : "s"}` : "All matching events"}</p>
          <ol className={styles.preview}>{ruleSteps(rule).map((step, index) => <li key={index}><span>{index + 1}.</span><strong>{actionNames[step.action]}</strong>{step.action_text && step.action !== "assign_owner" && <span className={styles.previewText}>{step.action_text}</span>}<span>{step.delay_minutes ? `After ${step.delay_minutes.toLocaleString("en-IN")} min` : "No delay"}</span></li>)}</ol>
          <div className={styles.actions}>{canManage && <><button className="button secondary" type="button" onClick={() => { setEditor(rule); setNotice(""); }}>Edit workflow</button><button className="button subtle" type="button" disabled={!!mutation} onClick={() => rule.enabled ? setConfirm({ type: "pause", rule }) : void toggleRule(rule)}>{mutation === rule.id ? "Updating…" : rule.enabled ? "Pause" : "Enable"}</button></>}<button className="button subtle" type="button" onClick={() => { setRuleFilter({ id: rule.id, name: rule.name }); setHistoryOffset(0); setTab("history"); }}>View executions</button></div>
        </article>) : <div className={styles.empty}><h3>{(query || ruleStatus) ? "No workflows match these filters" : "Your next follow-up can start here"}</h3><p>{(query || ruleStatus) ? "Try another name or clear the filters." : "Create a workflow for a new lead, a won deal or an incoming support ticket."}</p>{(query || ruleStatus) && <button className="button secondary" type="button" onClick={() => { setSearch(""); setQuery(""); setRuleStatus(""); setOffset(0); }}>Clear filters</button>}</div>}
        {rules.data && <Pagination offset={offset} total={rules.data.total} onChange={setOffset} />}
      </section>
    </> : <ExecutionHistory revision={revision} canManage={canManage} ruleFilter={ruleFilter} onClearRule={() => { setRuleFilter(null); setHistoryOffset(0); }} status={status} onStatus={value => { setStatus(value); setHistoryOffset(0); }} entity={entity} onEntity={value => { setEntity(value); setHistoryOffset(0); }} offset={historyOffset} onOffset={setHistoryOffset} search={historySearch} onSearch={setHistorySearch} query={historyQuery} onQuery={value => { setHistoryQuery(value); setHistoryOffset(0); }} onRefresh={() => setRevision(value => value + 1)} mutation={mutation} onRetry={job => void jobAction(job, "retry")} onCancel={job => setConfirm({ type: "cancel", job })} />}
    <p className={styles.note}>Scheduled steps are saved on the server and run while the local API is running. Email and external messaging are separate integrations.</p>
  </div>;

  async function toggleRule(rule: Rule) {
    if (mutationRef.current) return;
    mutationRef.current = true; setMutation(rule.id); setError(""); setNotice("");
    try { await api(`/automations/${rule.id}`, { method: "PATCH", body: JSON.stringify({ enabled: !rule.enabled }) }); setConfirm(null); setNotice(`“${rule.name}” ${rule.enabled ? "paused; pending work cancelled" : "enabled for future events"}.`); setRevision(value => value + 1); if (editor !== "new" && editor?.id === rule.id) setEditor(null); }
    catch (failure) { setError(errorText(failure)); }
    finally { mutationRef.current = false; setMutation(""); }
  }
  async function jobAction(job: Job, action: "retry" | "cancel") {
    if (mutationRef.current) return;
    mutationRef.current = true; setMutation(job.id); setError(""); setNotice("");
    try { await api(`/automations/jobs/${job.id}/${action}`, { method: "POST", headers: { "Idempotency-Key": `${job.id}-${action}-${job.attempts}` } }); setConfirm(null); setNotice(action === "retry" ? "Retry requested. Refresh history to see the result." : "Execution cancelled. Completed steps were kept."); setRevision(value => value + 1); }
    catch (failure) { setError(errorText(failure)); }
    finally { mutationRef.current = false; setMutation(""); }
  }
}

function ExecutionHistory({ revision, canManage, ruleFilter, onClearRule, status, onStatus, entity, onEntity, offset, onOffset, search, onSearch, query, onQuery, onRefresh, mutation, onRetry, onCancel }: { revision: number; canManage: boolean; ruleFilter: { id: string; name: string } | null; onClearRule: () => void; status: string; onStatus: (value: string) => void; entity: string; onEntity: (value: string) => void; offset: number; onOffset: (value: number) => void; search: string; onSearch: (value: string) => void; query: string; onQuery: (value: string) => void; onRefresh: () => void; mutation: string; onRetry: (job: Job) => void; onCancel: (job: Job) => void }) {
  const [view, setView] = useState("steps");
  const params = new URLSearchParams({ q: query, limit: String(pageSize), offset: String(offset) });
  if (ruleFilter) params.set("rule_id", ruleFilter.id);
  if (status) params.set("status", status);
  if (entity) params.set("entity_type", entity);
  const jobs = useRemote<Page<Job>>(view === "steps" ? `/automations/jobs?${params}` : null, revision);
  return <section aria-label="Execution history" className={styles.history}>
    <div className={styles.sectionHeader}><div><h3>Execution history</h3><p>Every step, its source record and the result recorded by the server.</p></div><button className="button secondary" type="button" onClick={onRefresh}>Refresh history</button></div>
    {ruleFilter && <div className={styles.activeFilter}><span>Workflow: <strong>{ruleFilter.name}</strong></span><button className="button subtle" type="button" onClick={onClearRule}>Show all workflows</button></div>}
    <form className={styles.filters} onSubmit={event => { event.preventDefault(); onQuery(search.trim()); }}>
      <label>History view<Select value={view} onValueChange={value => { setView(value); onOffset(0); }}><option value="steps">Individual steps</option><option value="runs">Workflow runs</option></Select></label>
      <label className={styles.search}>Search executions<input type="search" maxLength={200} value={search} onChange={event => onSearch(event.target.value)} placeholder="Workflow or source record" /></label>
      <label>Status<Select value={status} onValueChange={onStatus}><option value="">All statuses</option>{Object.entries(statusNames).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</Select></label>
      <label>Source<Select value={entity} onValueChange={onEntity}><option value="">All records</option><option value="leads">Leads</option><option value="deals">Deals</option><option value="tickets">Support tickets</option><option value="activities">Activities</option></Select></label>
      <button className="button secondary" type="submit">Search</button>
    </form>
    {view === "runs" ? <RunHistory path={`/automations/runs?${params}`} revision={revision} offset={offset} onOffset={onOffset} onRefresh={onRefresh} /> : <><div className={styles.tableWrap} aria-busy={jobs.loading}>
      {jobs.error ? <div className={styles.error} role="alert">{jobs.error}<button className="button secondary" type="button" onClick={onRefresh}>Try again</button></div> : jobs.loading ? <p className={styles.empty} role="status">Loading execution history…</p> : !jobs.data?.items.length ? <div className={styles.empty}><h3>No executions to show</h3><p>{query || status || entity || ruleFilter ? "Try another filter or wait for a matching CRM event." : "Enabled workflows start when their selected event happens. Existing records do not trigger new workflows automatically."}</p></div> : <table><thead><tr><th scope="col">Workflow / step</th><th scope="col">Source record</th><th scope="col">Status / timing</th><th scope="col">Result</th>{canManage && <th scope="col">Actions</th>}</tr></thead><tbody>{jobs.data.items.map(job => {
        const sourceHref = recordHref(job.entity_type, job.entity_id);
        const resultHref = recordHref(job.result_entity_type ?? "", job.result_entity_id ?? "");
        return <tr key={job.id}><th scope="row"><strong>{job.rule_name}</strong><span>Step {job.step_index} · {actionNames[job.action]}</span>{job.trigger && <span>{eventNames[job.trigger] ?? job.trigger}</span>}</th><td>{sourceHref ? <Link href={sourceHref}>{job.entity_name || "Open source record"}</Link> : job.entity_name || "Source unavailable"}<span>{job.entity_type === "activities" ? "Activity" : job.entity_type === "tickets" ? "Support ticket" : job.entity_type === "leads" ? "Lead" : "Deal"}</span></td><td><strong className={`${styles.status} ${styles[job.status]}`}>{statusNames[job.status]}</strong><span>{job.status === "queued" ? job.scheduled_at ? formatTimestamp(job.scheduled_at) : "Waiting for previous step" : formatTimestamp(job.completed_at ?? job.started_at ?? job.scheduled_at)}</span>{job.attempts > 0 && <span>{job.attempts} attempt{job.attempts === 1 ? "" : "s"}</span>}</td><td>{resultHref ? <Link href={resultHref}>{job.result || "Open result"}</Link> : job.result || (job.status === "queued" ? "Awaiting execution" : "—")}{job.error_detail && <details className={styles.failure}><summary>View details</summary><p>{job.error_detail}</p></details>}</td>{canManage && <td><div className={styles.actions}>{job.status === "failed" && job.attempts < 10 && <button className="button secondary" type="button" disabled={!!mutation} onClick={() => onRetry(job)}>{mutation === job.id ? "Updating…" : "Retry"}</button>}{["queued", "failed"].includes(job.status) && <button className="button subtle" type="button" disabled={!!mutation} onClick={() => onCancel(job)}>Cancel execution</button>}{job.status === "failed" && job.attempts >= 10 && <span>Retry limit reached</span>}{!["queued", "failed"].includes(job.status) && <span>No pending action</span>}</div></td>}</tr>;
      })}</tbody></table>}
    </div>
    {jobs.data && <Pagination offset={offset} total={jobs.data.total} onChange={onOffset} />}</>}
  </section>;
}

function RunHistory({ path, revision, offset, onOffset, onRefresh }: { path: string; revision: number; offset: number; onOffset: (offset: number) => void; onRefresh: () => void }) {
  const runs = useRemote<Page<Run>>(path, revision);
  return <>
    <p className={styles.note}>One summary per triggering event, including earlier single-action workflows. Choose Individual steps to inspect scheduled work or retry a failed step.</p>
    <div className={styles.tableWrap} aria-busy={runs.loading}>
      {runs.error ? <div className={styles.error} role="alert">{runs.error}<button className="button secondary" type="button" onClick={onRefresh}>Try again</button></div> : runs.loading ? <p className={styles.empty} role="status">Loading workflow runs…</p> : !runs.data?.items.length ? <div className={styles.empty}><h3>No workflow runs match</h3><p>Try another filter, or wait for a matching CRM event.</p></div> : <table><thead><tr><th scope="col">Workflow</th><th scope="col">Source record</th><th scope="col">Status</th><th scope="col">Started / completed</th><th scope="col">Result</th></tr></thead><tbody>{runs.data.items.map(run => {
        const sourceHref = recordHref(run.entity_type, run.entity_id);
        return <tr key={run.id}><th scope="row"><strong>{run.rule_name || "Earlier workflow"}</strong></th><td>{sourceHref ? <Link href={sourceHref}>{run.entity_name || "Open source record"}</Link> : run.entity_name || "Source unavailable"}</td><td><strong className={`${styles.status} ${styles[run.status]}`}>{statusNames[run.status]}</strong></td><td>{formatTimestamp(run.created_at)}{run.completed_at && <span>Completed {formatTimestamp(run.completed_at)}</span>}</td><td>{run.result || "No result recorded"}</td></tr>;
      })}</tbody></table>}
    </div>
    {runs.data && <Pagination offset={offset} total={runs.data.total} onChange={onOffset} />}
  </>;
}
