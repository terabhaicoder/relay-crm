"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, idempotencyRequest } from "@/lib/api/client";
import { Select } from "./ui/select";
import styles from "./saved-views.module.css";

export type SavedViewFilters = {
  q: string;
  status: string;
  sort: string;
  pipeline_id?: string | null;
  view?: string | null;
};
type SavedView = { id: string; name: string; entity: string; filters: SavedViewFilters; version: number };
type Props = { entity: string; filters: SavedViewFilters; onApply: (filters: SavedViewFilters) => void };

function normalized(entity: string, value: SavedViewFilters): SavedViewFilters {
  return {
    q: value.q, status: value.status, sort: value.sort,
    ...(entity === "deals" && value.pipeline_id ? { pipeline_id: value.pipeline_id } : {}),
    ...(entity === "deals" && value.view ? { view: value.view } : {}),
  };
}

export function SavedViews({ entity, filters, onApply }: Props) {
  const [items, setItems] = useState<SavedView[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState("");
  const [loadedRequest, setLoadedRequest] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const retryKey = useRef<ReturnType<typeof idempotencyRequest> | null>(null);
  const currentEntity = useRef<string | null>(entity);
  const requestId = `${entity}:${page}:${revision}`;
  const loading = loadedRequest !== requestId;
  const active = items.find(item => item.id === selected);
  const modified = active && JSON.stringify(normalized(entity, active.filters)) !== JSON.stringify(normalized(entity, filters));

  useEffect(() => {
    currentEntity.current = entity;
    return () => { currentEntity.current = null; };
  }, [entity]);

  useEffect(() => {
    const controller = new AbortController();
    void api<{ items: SavedView[]; total: number }>(`/saved-views?${new URLSearchParams({ entity, limit: "50", offset: String(page * 50) })}`, { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) { setItems(result.items); setTotal(result.total); setError(""); } })
      .catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Could not load saved views."); })
      .finally(() => { if (!controller.signal.aborted) setLoadedRequest(requestId); });
    return () => controller.abort();
  }, [entity, page, revision, requestId]);

  function choose(id: string) {
    setSelected(id); setEditing(false); setConfirmDelete(false); setNotice(""); setError("");
    const chosen = items.find(item => item.id === id);
    if (chosen) { onApply(chosen.filters); setNotice(`Applied “${chosen.name}”.`); }
  }

  async function save(event: FormEvent, asNew = false) {
    event.preventDefault();
    if (busy || !name.trim()) return;
    const requestEntity = entity;
    const update = active && !asNew;
    const body = { name: name.trim(), filters: normalized(entity, filters), ...(update ? { version: active.version } : { entity }) };
    setBusy(true); setError(""); setNotice("");
    retryKey.current = idempotencyRequest(body, retryKey.current);
    try {
      const saved = await api<SavedView>(update ? `/saved-views/${active.id}` : "/saved-views", {
        method: update ? "PATCH" : "POST", body: JSON.stringify(body),
        headers: { "Idempotency-Key": retryKey.current.key },
      });
      if (currentEntity.current !== requestEntity) return;
      setItems(current => [...current.filter(item => item.id !== saved.id), saved].sort((a, b) => a.name.localeCompare(b.name)));
      if (!update) setTotal(current => current + 1);
      setSelected(saved.id); setEditing(false); retryKey.current = null;
      setNotice(`Saved “${saved.name}” for you.`);
    } catch (reason) {
      if (currentEntity.current === requestEntity) setError(reason instanceof Error ? reason.message : "Could not save this view. Please retry.");
    } finally {
      if (currentEntity.current === requestEntity) setBusy(false);
    }
  }

  async function remove() {
    if (!active || busy) return;
    const requestEntity = entity;
    setBusy(true); setError("");
    try {
      await api<null>(`/saved-views/${active.id}`, { method: "DELETE" });
      if (currentEntity.current !== requestEntity) return;
      setItems(current => current.filter(item => item.id !== active.id));
      setTotal(current => Math.max(0, current - 1)); setSelected(""); setConfirmDelete(false);
      if (page > 0 && items.length === 1) setPage(current => current - 1);
      setNotice(`Deleted “${active.name}”. Your current filters are unchanged.`);
    } catch (reason) {
      if (currentEntity.current === requestEntity) setError(reason instanceof Error ? reason.message : "Could not delete this saved view.");
    } finally {
      if (currentEntity.current === requestEntity) setBusy(false);
    }
  }

  return <section className={styles.root} aria-label="Personal saved views">
    <div className={styles.controls}>
      <label className={styles.label}>Saved views<Select aria-label="Saved view" value={active?.id ?? ""} onValueChange={choose} disabled={loading || busy}>
        <option value="">{loading ? "Loading views…" : "Current filters"}</option>
        {items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
      </Select></label>
      <button type="button" className="button" disabled={busy || loading} onClick={() => { setName(active?.name ?? ""); setEditing(true); setConfirmDelete(false); setNotice(""); setError(""); retryKey.current = null; }}>Save current view</button>
      {active && <button type="button" className="button" disabled={busy} onClick={() => { setConfirmDelete(true); setEditing(false); setNotice(""); }}>Delete saved view</button>}
      {modified && <span className={styles.hint}>Filters changed</span>}
      {total > 50 && <div className={styles.pages}><button type="button" className="button" disabled={page === 0 || loading || busy} onClick={() => { setPage(current => current - 1); setSelected(""); }}>Previous views</button><span>{page + 1} / {Math.ceil(total / 50)}</span><button type="button" className="button" disabled={(page + 1) * 50 >= total || loading || busy} onClick={() => { setPage(current => current + 1); setSelected(""); }}>More views</button></div>}
    </div>
    {editing && <form className={styles.editor} onSubmit={event => void save(event)}>
      <label>View name<input autoFocus required maxLength={80} value={name} onChange={event => setName(event.target.value)} placeholder="For example, qualified website leads" disabled={busy} /></label>
      <div className={styles.actions}><button className="button primary" type="submit" disabled={busy || !name.trim()}>{busy ? "Saving…" : active ? "Update view" : "Save view"}</button>
        {active && <button className="button" type="button" disabled={busy || !name.trim()} onClick={event => void save(event, true)}>Save as new</button>}
        <button className="button" type="button" disabled={busy} onClick={() => setEditing(false)}>Cancel</button>
        <span className={styles.hint}>Only you can see this view.</span></div>
    </form>}
    {confirmDelete && active && <div className={styles.confirm}><span>Delete “{active.name}”?</span><button type="button" className="button danger" disabled={busy} onClick={() => void remove()}>{busy ? "Deleting…" : "Delete view"}</button><button type="button" className="button" disabled={busy} onClick={() => setConfirmDelete(false)}>Cancel</button></div>}
    {error && <div className={styles.feedback} role="alert">{error}<button type="button" className="button" disabled={busy} onClick={() => setRevision(current => current + 1)}>Reload views</button></div>}
    {notice && <p className={styles.notice} role="status">{notice}</p>}
  </section>;
}
