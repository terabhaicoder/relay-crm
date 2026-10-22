"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, formatTimestamp, text, type Row } from "@/lib/api/client";

export function EngagementRecordDrafts({ entity, recordId }: { entity: string; recordId: string }) {
  const [page, setPage] = useState(0);
  const [retry, setRetry] = useState(0);
  const [result, setResult] = useState<{ key: string; items?: Row[]; total?: number; error?: string }>({ key: "" });
  const key = `${entity}/${recordId}/${page}/${retry}`;
  const ready = result.key === key;
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ entity_type: entity, entity_id: recordId, limit: "5", offset: String(page * 5) });
    api<{ items: Row[]; total: number }>(`/email/messages?${params}`, { signal: controller.signal })
      .then(data => setResult({ key, ...data }))
      .catch((failure: Error) => { if (!controller.signal.aborted) setResult({ key, error: failure.message }); });
    return () => controller.abort();
  }, [entity, recordId, page, key]);
  return <section className="context-action" aria-label="Linked email drafts">
    <h3>Email drafts for this record</h3>
    <p>Saved correspondence, linked to this customer context. These messages have not been sent.</p>
    {!ready ? <p role="status">Loading linked drafts…</p> : result.error ? <p role="alert">{result.error} <button type="button" className="button subtle" onClick={() => setRetry(value => value + 1)}>Retry drafts</button></p> : <>
      {!result.items?.length ? <p>No linked drafts yet.</p> : <div className="timeline">{result.items.map(draft => <article key={draft.id}><Link className="text-link" href={`/communications?id=${encodeURIComponent(draft.id)}`}>{text(draft.subject)}</Link><p>{text(draft.recipient)} · Unsent draft</p><small>{formatTimestamp(draft.created_at)}</small></article>)}</div>}
      {(result.total ?? 0) > 5 && <div className="pagination"><span>{page * 5 + 1}–{Math.min((page + 1) * 5, result.total!)} of {result.total}</span><button type="button" className="button subtle" disabled={!page} onClick={() => setPage(value => value - 1)}>Previous drafts</button><button type="button" className="button subtle" disabled={(page + 1) * 5 >= result.total!} onClick={() => setPage(value => value + 1)}>Next drafts</button></div>}
    </>}
  </section>;
}
