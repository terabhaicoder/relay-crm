"use client";

import Link from "next/link";
import { useEffect, useId, useState } from "react";
import { api, amount, formatTimestamp, text, type Row } from "@/lib/api/client";
import { Icon } from "./icon";
import styles from "./customer-context.module.css";

type Section = "contacts" | "deals" | "activities" | "tickets" | "leads" | "timeline";
type Collection = { items: Row[]; total: number };
type Overview = {
  record: Row;
  sections: Record<Exclude<Section, "timeline">, Collection>;
  summary: { open_deals: number; won_deals: number; open_pipeline: string; won_revenue: string; open_tickets: number };
  timeline: Collection;
};
export type CustomerContextProps = {
  entity: "parties" | "contacts";
  entityId: string;
  refreshKey?: string | number;
  onCreate?: (entity: "deals" | "activities" | "tickets", defaults: Record<string, string>) => void;
};
const titles: Record<Section, string> = { contacts: "Contacts", deals: "Deals", activities: "Activities", tickets: "Support", leads: "Original leads", timeline: "History" };
const route = (entity: string) => entity === "parties" ? "accounts" : entity;
const pageSize = 10;

export function CustomerContext({ entity, entityId, refreshKey = "", onCreate }: CustomerContextProps) {
  const [section, setSection] = useState<Section>("deals");
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const [result, setResult] = useState<{ key: string; data?: Overview; error?: string } | null>(null);
  const tabId = useId();
  const requestKey = `${entity}/${entityId}/${refreshKey}/${offset}/${retry}`;
  const ready = result?.key === requestKey;
  const data = ready ? result.data : undefined;
  const error = ready ? result.error : undefined;
  const collection = data ? section === "timeline" ? data.timeline : data.sections[section] : undefined;
  const tabs: Section[] = ["deals", "contacts", "activities", "tickets", "leads", "timeline"];

  useEffect(() => {
    const controller = new AbortController();
    api<Overview>(`/${entity}/${encodeURIComponent(entityId)}/overview?limit=${pageSize}&offset=${offset}`, { signal: controller.signal })
      .then(data => setResult({ key: requestKey, data }))
      .catch((failure: Error) => { if (!controller.signal.aborted) setResult({ key: requestKey, error: failure.message }); });
    return () => controller.abort();
  }, [entity, entityId, offset, requestKey]);

  function create(target: "deals" | "activities" | "tickets") {
    const defaults: Record<string, string> = target === "activities"
      ? { entity_type: entity, entity_id: entityId }
      : entity === "parties" ? { party_id: entityId }
        : { contact_id: entityId, ...(text(data?.record.party_id) ? { party_id: text(data?.record.party_id) } : {}) };
    onCreate?.(target, defaults);
  }
  function select(next: Section) { setSection(next); setOffset(0); }

  return <section className={styles.context} aria-label="Customer overview">
    <div className={styles.intro}>
      <h3>The whole customer relationship</h3>
      <p>Sales, follow-ups and support, connected to this {entity === "parties" ? "company" : "contact"}.</p>
    </div>
    {!ready && <p className={styles.state} role="status">Loading customer context…</p>}
    {error && <div className={styles.error} role="alert"><p>{error}</p><button type="button" className="button subtle" onClick={() => setRetry(retry + 1)}>Retry overview</button></div>}
    {data && <>
      <dl className={styles.summary}>
        <div><dt>Open pipeline · {data.summary.open_deals} deals</dt><dd>{amount(data.summary.open_pipeline)}</dd></div>
        <div><dt>Won revenue · {data.summary.won_deals} deals</dt><dd>{amount(data.summary.won_revenue)}</dd></div>
        <div><dt>Open support tickets</dt><dd>{data.summary.open_tickets}</dd></div>
      </dl>
      {onCreate && <div className={styles.actions}>
        <button type="button" className="button secondary" onClick={() => create("activities")}><Icon name="plus" size={14} />Add follow-up</button>
        <button type="button" className="button subtle" onClick={() => create("deals")}>Add deal</button>
        <button type="button" className="button subtle" onClick={() => create("tickets")}>Add ticket</button>
      </div>}
    </>}
    <div className={styles.tabs} role="tablist" aria-label="Related customer records">
      {tabs.map((name, index) => <button key={name} type="button" role="tab" id={`${tabId}-${name}`}
        aria-selected={section === name} aria-controls={`${tabId}-panel`} tabIndex={section === name ? 0 : -1}
        onClick={() => select(name)} onKeyDown={event => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
          event.preventDefault();
          const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
          select(tabs[next]!);
          document.getElementById(`${tabId}-${tabs[next]}`)?.focus();
        }}>{titles[name]}{data && <span>{name === "timeline" ? data.timeline.total : data.sections[name]?.total ?? 0}</span>}</button>)}
    </div>
    <div id={`${tabId}-panel`} role="tabpanel" aria-labelledby={`${tabId}-${section}`} className={styles.panel} aria-busy={!ready}>
      {collection && !collection.items.length && <p className={styles.state}>{offset ? "No more records on this page." : `No ${titles[section].toLowerCase()} linked yet.`}</p>}
      {collection && collection.items.length > 0 && <ul className={styles.records}>
        {collection.items.map(record => {
          const targetEntity = section === "timeline" ? text(record.entity_type) : section;
          const targetId = section === "timeline" ? text(record.entity_id) : record.id;
          const href = ["leads", "contacts", "parties", "deals", "activities", "tickets"].includes(targetEntity) && targetId
            ? `/${route(targetEntity)}?id=${encodeURIComponent(targetId)}` : undefined;
          const label = section === "timeline" ? text(record.entity_name || record.name || record.action).replaceAll("_", " ") : text(record.name);
          const detail = section === "timeline" ? [text(record.action).replaceAll("_", " "), formatTimestamp(record.created_at)].filter(Boolean).join(" · ")
            : section === "deals" ? `${amount(record.amount)} · ${text(record.status)}`
              : section === "activities" ? `${text(record.type)} · ${text(record.status)}${record.due_date ? ` · Due ${formatTimestamp(record.due_date)}` : ""}`
                : section === "tickets" ? `${text(record.status)} · ${text(record.priority)} priority`
                  : [text(record.email), text(record.phone), text(record.status)].filter(Boolean).join(" · ");
          const content = <><span><strong>{label || "Record activity"}</strong><small>{detail}</small></span>{href && <Icon name="arrow" size={15} />}</>;
          return <li key={record.id}>{href ? <Link href={href}>{content}</Link> : <div className={styles.unlinked}>{content}</div>}</li>;
        })}
      </ul>}
      {collection && collection.total > pageSize && <div className={styles.pagination}>
        <span>{offset + 1}–{Math.min(offset + pageSize, collection.total)} of {collection.total}</span>
        <button type="button" className="button subtle" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - pageSize))}>Previous</button>
        <button type="button" className="button subtle" disabled={offset + pageSize >= collection.total} onClick={() => setOffset(offset + pageSize)}>Next</button>
      </div>}
    </div>
  </section>;
}
