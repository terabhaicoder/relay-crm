"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, amount, formatTimestamp, type Row, text } from "@/lib/api/client";
import { Select } from "./ui/select";
import { Icon } from "./icon";
import styles from "./sales-workbench.module.css";

const queues = [
  { key: "overdue", name: "Overdue tasks", hint: "Pending tasks with a due date before today.", empty: "No overdue tasks. You're caught up.", path: "activities", icon: "clock" },
  { key: "today", name: "Due today", hint: "Pending tasks due today, in Asia/Kolkata time.", empty: "Nothing due today. Make room for your next conversation.", path: "activities", icon: "calendar" },
  { key: "upcoming", name: "Upcoming", hint: "Pending tasks with a future due date.", empty: "No upcoming tasks. Add a follow-up from any customer record.", path: "activities", icon: "activities" },
  { key: "follow_up_leads", name: "Lead follow-ups", hint: "Open leads with no follow-up scheduled, or one due today or earlier.", empty: "Every open lead has a future follow-up.", path: "leads", icon: "leads" },
  { key: "stale_deals", name: "Stalled deals", hint: "Open deals that have stayed in the same stage for more than 14 days.", empty: "No stalled deals. Keep the next step clear.", path: "deals", icon: "deals" },
  { key: "open_tickets", name: "Open support", hint: "Customer tickets that still need a resolution.", empty: "No open tickets in this view.", path: "tickets", icon: "tickets" },
  { key: "unassigned_tickets", name: "Unassigned support", hint: "Open tickets without an owner, across your accessible workspace.", empty: "Every open ticket has an owner.", path: "tickets", icon: "contacts" },
] as const;
type Queue = typeof queues[number]["key"];
type WorkbenchResponse = { items: Row[]; total: number; counts: Record<Queue, number> };
const pageSize = 15;

function dueLabel(value: unknown): string {
  const raw = text(value).trim();
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(raw);
  const normalized = raw.replace(" ", "T");
  const date = new Date(dateOnly ? `${raw}T00:00:00Z` : /(?:Z|[+-]\d{2}:?\d{2})$/i.test(normalized) ? normalized : `${normalized}Z`);
  if (Number.isNaN(date.getTime())) return `Due ${formatTimestamp(value)}`;
  const dayFormatter = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" });
  const dayKey = (day: Date) => {
    const parts = dayFormatter.formatToParts(day);
    return ["year", "month", "day"].map(part => parts.find(item => item.type === part)?.value).join("-");
  };
  const day = dateOnly ? raw : dayKey(date);
  const difference = Math.round((Date.parse(`${day}T00:00:00Z`) - Date.parse(`${dayKey(new Date())}T00:00:00Z`)) / 86400000);
  const label = difference === 0 ? "today" : difference === 1 ? "tomorrow" : difference === -1 ? "yesterday"
    : new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${day}T00:00:00Z`));
  const time = dateOnly ? "" : ` · ${new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(date)} IST`;
  return `Due ${label}${time}`;
}

export function SalesWorkbench({ userId, canWrite, onChanged }: { userId: string; canWrite: boolean; onChanged?: () => void }) {
  const [queue, setQueue] = useState<Queue>("overdue");
  const [scope, setScope] = useState("mine");
  const [page, setPage] = useState(0);
  const [data, setData] = useState<WorkbenchResponse | null>(null);
  const [loadedKey, setLoadedKey] = useState("");
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");
  const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0);
  const generation = useRef(0);
  const requestKey = `${queue}/${scope}/${page}/${userId}/${revision}`;
  const loading = loadedKey !== requestKey;
  const current = queues.find(item => item.key === queue)!;
  const reload = useCallback(() => setRevision(value => value + 1), []);

  useEffect(() => {
    const request = ++generation.current;
    const controller = new AbortController();
    const params = new URLSearchParams({ queue, limit: String(pageSize), offset: String(page * pageSize) });
    if (scope === "mine") params.set("owner_id", userId);
    void api<WorkbenchResponse>(`/workbench?${params}`, { signal: controller.signal }).then(result => {
      if (controller.signal.aborted || request !== generation.current) return;
      setError("");
      if (page > 0 && result.items.length === 0 && result.total > 0) {
        setPage(Math.max(0, Math.ceil(result.total / pageSize) - 1));
        return;
      }
      setData(result);
    }).catch(reason => {
      if (!controller.signal.aborted && request === generation.current) setError(reason instanceof Error ? reason.message : "Couldn't load your work. Please retry.");
    }).finally(() => { if (!controller.signal.aborted && request === generation.current) setLoadedKey(requestKey); });
    return () => controller.abort();
  }, [queue, scope, page, userId, revision, requestKey]);

  async function complete(row: Row) {
    if (busyId) return;
    setBusyId(row.id);
    setNotice("");
    setError("");
    try {
      await api(`/activities/${row.id}/complete`, { method: "POST" });
      setNotice(`${text(row.name) || "Task"} marked complete.`);
      reload();
      onChanged?.();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Couldn't complete this task. Please retry.");
    } finally { setBusyId(""); }
  }

  return <section className={styles.workbench} aria-label="Follow-up workbench">
    <div className={styles.topline}>
      <p>Pick the next conversation. Keep every promise in sight.</p>
      <div className={styles.actions}>
        <Select aria-label="Work scope" value={scope} disabled={loading || !!busyId} onChange={event => { setScope(event.target.value); setPage(0); setNotice(""); }}>
          <option value="mine">My work</option><option value="all">Workspace work</option>
        </Select>
        <button type="button" className="button" onClick={reload} disabled={loading}>Refresh</button>
      </div>
    </div>
    <div className={styles.layout}>
      <nav className={styles.queues} aria-label="Work queues">
        {queues.map(item => <button type="button" key={item.key} aria-current={queue === item.key ? "page" : undefined}
          onClick={() => { setQueue(item.key); setPage(0); setNotice(""); }}>
          <Icon name={item.icon} size={17} /><span>{item.name}</span>
          <strong>{loading ? "—" : data?.counts[item.key] ?? "—"}</strong>
        </button>)}
      </nav>
      <div className={styles.panel} aria-busy={loading}>
        <div className={styles.heading}><div><h2>{current.name}</h2><p>{current.hint}</p></div><Link href={`/${current.path}`}>View all <Icon name="arrow" size={16} /></Link></div>
        {notice && <p role="status" className={styles.notice}>{notice}</p>}
        {!loading && error && <div role="alert" className={styles.error}>{error} <button className="button" onClick={reload}>Retry</button></div>}
        {loading ? <div role="status" className={styles.empty}>Loading your work…</div> : !error && !data?.items.length ? <div className={styles.empty}><Icon name="check" size={26} /><h3>{current.empty}</h3><Link href={`/${current.path}`} className="button">Open {current.path === "activities" ? "tasks" : current.path === "tickets" ? "support" : current.path}</Link></div> : !error && <>
          <ul className={styles.rows}>{data?.items.map(row => {
            const entity = text(row.entity_type) || current.path;
            const path = entity === "parties" ? "accounts" : entity;
            const due = row.due_at ?? row.due_date ?? row.next_follow_up;
            return <li key={row.id}>
              {current.path === "activities" && canWrite && <button type="button" className={styles.complete} disabled={!!busyId} onClick={() => void complete(row)} aria-label={`Complete ${text(row.name)}`} title="Mark complete">{busyId === row.id ? "Saving…" : "Complete"}</button>}
              <div className={styles.record}><Link href={`/${path}?id=${encodeURIComponent(row.id)}`}>{text(row.name) || text(row.subject) || "Untitled record"}</Link><p>{[text(row.company_name), text(row.priority), text(row.status).replaceAll("_", " ")].filter(Boolean).join(" · ")}</p></div>
              <div className={styles.context}>{current.path === "deals" ? <><strong>{amount(row.amount)}</strong><span>In this stage since {formatTimestamp(row.stage_entered_at)}</span></> : due ? <span title={formatTimestamp(due)}>{dueLabel(due)}</span> : current.path === "leads" ? <span>No follow-up scheduled</span> : <span>Updated {formatTimestamp(row.updated_at)}</span>}</div>
              <Link className={styles.open} href={`/${path}?id=${encodeURIComponent(row.id)}`} aria-label={`Open ${text(row.name) || text(row.subject)}`}><Icon name="arrow" size={18} /></Link>
            </li>;
          })}</ul>
          <div className={styles.pagination}><span>{data?.total ? `${page * pageSize + 1}–${Math.min((page + 1) * pageSize, data.total)} of ${data.total}` : "0 records"}</span><div><button className="button" disabled={page === 0} onClick={() => setPage(value => value - 1)}>Previous</button><button className="button" disabled={(page + 1) * pageSize >= (data?.total ?? 0)} onClick={() => setPage(value => value + 1)}>Next</button></div></div>
        </>}
      </div>
    </div>
  </section>;
}
