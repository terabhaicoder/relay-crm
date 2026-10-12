"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { api, formatTimestamp, idempotencyRequest, text, type Row } from "@/lib/api/client";
import { Select } from "./ui/select";
import { Icon } from "./icon";
import styles from "./campaign-members.module.css";

type Member = { id: string; entity_type: "leads" | "contacts"; entity_id: string; created_at: string; record: Row };
type Members = { items: Member[]; total: number; summary: { members: number; leads: number; contacts: number; converted_leads: number; conversion_rate: string | number } };
type Results = { items: Row[]; total: number };
export type CampaignMembersProps = { campaignId: string; canEdit: boolean; refreshKey?: string | number };
const pageSize = 10;

export function CampaignMembers({ campaignId, canEdit, refreshKey = "" }: CampaignMembersProps) {
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<{ key: string; data?: Members; error?: string } | null>(null);
  const [kind, setKind] = useState<"leads" | "contacts">("leads");
  const [query, setQuery] = useState("");
  const [searchRevision, setSearchRevision] = useState(0);
  const [search, setSearch] = useState<{ key: string; data?: Results; error?: string } | null>(null);
  const [selected, setSelected] = useState<Row | null>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<{ error: boolean; message: string } | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  const controlId = useId();
  const key = `${campaignId}/${refreshKey}/${offset}/${revision}`;
  const ready = result?.key === key;
  const data = ready ? result.data : undefined;
  const error = ready ? result.error : undefined;
  const searchKey = `${kind}/${query}/${searchRevision}`;
  const searchReady = search?.key === searchKey;

  useEffect(() => {
    const controller = new AbortController();
    api<Members>(`/campaigns/${encodeURIComponent(campaignId)}/members?limit=${pageSize}&offset=${offset}`, { signal: controller.signal })
      .then(data => setResult({ key, data }))
      .catch((failure: Error) => { if (!controller.signal.aborted) setResult({ key, error: failure.message }); });
    return () => controller.abort();
  }, [campaignId, offset, key]);

  useEffect(() => {
    if (!canEdit || query.trim().length < 2 || selected) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api<Results>(`/${kind}?q=${encodeURIComponent(query.trim())}&limit=10&offset=0`, { signal: controller.signal })
        .then(data => setSearch({ key: searchKey, data }))
        .catch((failure: Error) => { if (!controller.signal.aborted) setSearch({ key: searchKey, error: failure.message }); });
    }, 250);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [canEdit, kind, query, selected, searchKey]);

  async function add() {
    if (!selected || busy) return;
    setBusy(true); setFeedback(null);
    const body = { entity_type: kind, entity_id: selected.id };
    request.current = idempotencyRequest(body, request.current);
    try {
      await api(`/campaigns/${encodeURIComponent(campaignId)}/members`, { method: "POST", body: JSON.stringify(body), headers: { "Idempotency-Key": request.current.key } });
      setFeedback({ error: false, message: `${text(selected.name)} is a campaign member.` });
      setSelected(null); setQuery(""); setOffset(0); setRevision(value => value + 1);
      request.current = null;
    } catch (failure) { setFeedback({ error: true, message: (failure as Error).message }); }
    finally { setBusy(false); }
  }
  async function remove(member: Member) {
    if (busy) return;
    setBusy(true); setFeedback(null);
    try {
      await api(`/campaigns/${encodeURIComponent(campaignId)}/members/${encodeURIComponent(member.id)}`, { method: "DELETE" });
      setFeedback({ error: false, message: `${text(member.record.name)} was removed from this campaign. Their CRM record is unchanged.` });
      setRemoving(null);
      if (data?.items.length === 1 && offset) setOffset(Math.max(0, offset - pageSize));
      setRevision(value => value + 1);
    } catch (failure) { setFeedback({ error: true, message: (failure as Error).message }); }
    finally { setBusy(false); }
  }

  return <section className={styles.members} aria-label="Campaign members">
    <header className={styles.intro}><h3>The people behind this campaign</h3><p>Connect leads and contacts, then track which leads become customers.</p></header>
    {!ready && <p className={styles.state} role="status">Loading campaign members…</p>}
    {error && <div role="alert" className={styles.error}><p>{error}</p><button type="button" className="button subtle" onClick={() => setRevision(value => value + 1)}>Retry members</button></div>}
    {data && <><dl className={styles.summary}>
      <div><dt>Members</dt><dd>{data.summary.members}</dd></div>
      <div><dt>Leads converted</dt><dd>{data.summary.converted_leads}<span> / {data.summary.leads}</span></dd></div>
      <div><dt>Lead conversion</dt><dd>{data.summary.leads ? `${data.summary.conversion_rate}%` : "—"}</dd></div>
    </dl><p className={styles.caption}>{data.summary.leads} leads · {data.summary.contacts} contacts. Conversion reflects linked lead status; it does not claim campaign-attributed revenue.</p></>}
    {canEdit && <div className={styles.add}>
      <h4>Add a campaign member</h4>
      <div className={styles.searchControls}>
        <label htmlFor={`${controlId}-kind`}>Record type<Select id={`${controlId}-kind`} value={kind} disabled={busy} onValueChange={value => { setKind(value as "leads" | "contacts"); setSelected(null); setQuery(""); }}><option value="leads">Lead</option><option value="contacts">Contact</option></Select></label>
        <label htmlFor={`${controlId}-search`}>Find a {kind === "leads" ? "lead" : "contact"}<input id={`${controlId}-search`} type="search" value={query} disabled={busy} placeholder="Name, email or phone…" autoComplete="off" aria-describedby={`${controlId}-help`} onChange={event => { setQuery(event.target.value); setSelected(null); }} /></label>
      </div>
      <p id={`${controlId}-help`} className={styles.caption}>Type at least two characters to search existing records.</p>
      {query.trim().length >= 2 && !selected && <div className={styles.results}>
        {!searchReady && <p className={styles.state} role="status">Searching {kind}…</p>}
        {searchReady && search.error && <div className={styles.error} role="alert"><p>{search.error}</p><button className="button subtle" type="button" onClick={() => setSearchRevision(value => value + 1)}>Retry search</button></div>}
        {searchReady && search.data && (search.data.items.length ? <><ul>{search.data.items.map(record => <li key={record.id}><button type="button" disabled={busy} onClick={() => { setSelected(record); setQuery(text(record.name)); }}><span><strong>{text(record.name)}</strong><small>{[text(record.email), text(record.company), text(record.phone)].filter(Boolean).join(" · ") || "No contact details added"}</small></span><Icon name="plus" size={15} /></button></li>)}</ul>{search.data.total > 10 && <p className={styles.caption}>Showing the first 10 matches. Refine your search for more specific results.</p>}</> : <p className={styles.state}>No matching {kind}. Create the record first, or try another search.</p>)}
      </div>}
      {selected && <div className={styles.selection}><div><strong>{text(selected.name)}</strong><small>{text(selected.email) || text(selected.phone) || (kind === "leads" ? "Lead" : "Contact")}</small></div><button type="button" className="button secondary" disabled={busy} onClick={() => void add()}>{busy ? "Adding…" : "Add member"}</button><button type="button" className="icon-button" aria-label="Clear selected member" disabled={busy} onClick={() => { setSelected(null); setQuery(""); }}><Icon name="close" size={15} /></button></div>}
    </div>}
    {feedback && <p role={feedback.error ? "alert" : "status"} className={feedback.error ? styles.error : styles.success}>{feedback.message}</p>}
    {data && <div className={styles.list}>
      <h4>Campaign members <span>{data.total}</span></h4>
      {!data.items.length && <p className={styles.state}>No members yet. {canEdit ? "Add the people this campaign reaches." : "Campaign members will appear here."}</p>}
      <ul>{data.items.map(member => <li key={member.id}>
        <div className={styles.memberRow}><Link href={`/${member.entity_type}?id=${encodeURIComponent(member.entity_id)}`}><strong>{text(member.record.name)}</strong><small>{member.entity_type === "leads" ? `Lead · ${text(member.record.status)}` : "Contact"}{member.record.email ? ` · ${text(member.record.email)}` : ""}</small><small>Added {formatTimestamp(member.created_at)}</small></Link>{canEdit && <button type="button" className={styles.remove} aria-label={`Remove ${text(member.record.name)} from campaign`} disabled={busy} onClick={() => setRemoving(member.id)}>Remove</button>}</div>
        {removing === member.id && <div className={styles.confirm}><p>Remove this campaign membership? The original {member.entity_type === "leads" ? "lead" : "contact"} stays in your CRM.</p><button type="button" className="button subtle" disabled={busy} onClick={() => setRemoving(null)}>Keep member</button><button type="button" className="button secondary" disabled={busy} onClick={() => void remove(member)}>{busy ? "Removing…" : "Remove member"}</button></div>}
      </li>)}</ul>
      {data.total > pageSize && <div className={styles.pagination}><span>{offset + 1}–{Math.min(offset + pageSize, data.total)} of {data.total}</span><button type="button" className="button subtle" disabled={!offset || busy} onClick={() => setOffset(Math.max(0, offset - pageSize))}>Previous</button><button type="button" className="button subtle" disabled={offset + pageSize >= data.total || busy} onClick={() => setOffset(offset + pageSize)}>Next</button></div>}
    </div>}
  </section>;
}
