"use client";

import { useEffect, useRef, useState } from "react";
import { api, formatTimestamp, idempotencyRequest } from "@/lib/api/client";
import type { CustomDefinitionList, CustomDefinitionResponse, CustomRecordResponse } from "@/lib/api/schema";
import { Select } from "./ui/select";
import styles from "./custom-fields.module.css";

const collections = [{ value: "leads", label: "Leads" }, { value: "contacts", label: "Contacts" }, { value: "parties", label: "Companies" }, { value: "deals", label: "Deals" }, { value: "tickets", label: "Tickets" }];
const types = [{ value: "text", label: "Text" }, { value: "number", label: "Number" }, { value: "date", label: "Date" }, { value: "boolean", label: "Yes / No" }, { value: "select", label: "Choice" }];
const reason = (error: unknown) => error instanceof Error ? error.message : "Could not save your changes. Please retry.";

export function CustomFieldSettings({ canManage }: { canManage: boolean }) {
  const [entity, setEntity] = useState("leads");
  return <section className={styles.root} aria-label="Custom field settings">
    <div className={styles.heading}><div><h2>Custom fields</h2><p>Add the details your team needs on each record. Fields are optional and saved separately from the main record.</p></div>
      <label>Record type<Select value={entity} onValueChange={setEntity} aria-label="Custom field record type">{collections.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</Select></label>
    </div>
    <DefinitionList key={entity} entity={entity} canManage={canManage} />
  </section>;
}

function DefinitionList({ entity, canManage }: { entity: string; canManage: boolean }) {
  const [data, setData] = useState<CustomDefinitionList | null>(null);
  const [page, setPage] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loaded, setLoaded] = useState("");
  const [error, setError] = useState("");
  const [editor, setEditor] = useState<CustomDefinitionResponse | "new" | null>(null);
  const request = `${entity}:${page}:${revision}`;
  useEffect(() => {
    const controller = new AbortController();
    void api<CustomDefinitionList>(`/custom-fields/definitions?${new URLSearchParams({ entity, include_archived: "true", limit: "20", offset: String(page * 20) })}`, { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) { setData(result); setError(""); } })
      .catch(error => { if (!controller.signal.aborted) setError(reason(error)); })
      .finally(() => { if (!controller.signal.aborted) setLoaded(request); });
    return () => controller.abort();
  }, [entity, page, revision, request]);
  return <>
    <div className={styles.actions}>{canManage && <button type="button" className="button primary" onClick={() => setEditor("new")}>Add custom field</button>}<span className={styles.hint}>{canManage ? "Field keys and types stay fixed to protect existing values." : "An owner or administrator can manage fields."}</span></div>
    {editor && <DefinitionEditor key={editor === "new" ? "new" : editor.id} entity={entity} field={editor === "new" ? undefined : editor} onCancel={() => setEditor(null)} onSaved={() => { setEditor(null); setRevision(value => value + 1); }} />}
    {loaded !== request ? <p role="status">Loading custom fields…</p> : error ? <p role="alert">{error} <button className="button" type="button" onClick={() => setRevision(value => value + 1)}>Retry</button></p> : data?.items.length ? <ul className={styles.list}>{data.items.map(field => <li key={field.id}><div><strong>{field.label}</strong><span className={styles.meta}>{types.find(type => type.value === field.field_type)?.label} · {field.field_key}{field.archived ? " · Archived" : ""}</span>{field.description && <p>{field.description}</p>}</div>{canManage && <button type="button" className="button" onClick={() => setEditor(field)}>Manage {field.label}</button>}</li>)}</ul> : <div className={styles.empty}><h3>No custom fields yet</h3><p>Add a field for details such as a renewal date, region or qualification score.</p></div>}
    {(data?.total ?? 0) > 20 && <div className={styles.actions}><button type="button" className="button" disabled={page === 0 || loaded !== request} onClick={() => setPage(value => value - 1)}>Previous fields</button><span>Page {page + 1} of {Math.ceil((data?.total ?? 0) / 20)}</span><button type="button" className="button" disabled={(page + 1) * 20 >= (data?.total ?? 0) || loaded !== request} onClick={() => setPage(value => value + 1)}>More fields</button></div>}
  </>;
}

function DefinitionEditor({ entity, field, onCancel, onSaved }: { entity: string; field?: CustomDefinitionResponse; onCancel: () => void; onSaved: () => void }) {
  const [label, setLabel] = useState(field?.label ?? "");
  const [fieldKey, setFieldKey] = useState(field?.field_key ?? "");
  const [fieldType, setFieldType] = useState(field?.field_type ?? "text");
  const [description, setDescription] = useState(field?.description ?? "");
  const [choices, setChoices] = useState(field?.options.join("\n") ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirmArchive, setConfirmArchive] = useState(false);
  const retry = useRef<ReturnType<typeof idempotencyRequest> | null>(null);
  async function save(archive?: boolean) {
    if (busy) return;
    const options = fieldType === "select" ? choices.split("\n").map(value => value.trim()).filter(Boolean) : [];
    const body = archive !== undefined && field ? { version: field.version, archived: archive } : {
      label: label.trim(), description: description.trim(), options,
      ...(field ? { version: field.version } : { entity, field_key: fieldKey.trim(), field_type: fieldType }),
    };
    setBusy(true); setError(""); retry.current = idempotencyRequest(body, retry.current);
    try { await api(field ? `/custom-fields/definitions/${field.id}` : "/custom-fields/definitions", { method: field ? "PATCH" : "POST", body: JSON.stringify(body), headers: { "Idempotency-Key": retry.current.key } }); onSaved(); }
    catch (error) { setError(reason(error)); }
    finally { setBusy(false); }
  }
  return <div className={styles.editor} aria-label={field ? `Manage ${field.label}` : "New custom field"}>
    <h3>{field ? `Manage ${field.label}` : "New custom field"}</h3>
    <div className={styles.grid}>
      <label>Field label<input value={label} maxLength={100} disabled={busy} onChange={event => setLabel(event.target.value)} /></label>
      <label>Field key<input value={fieldKey} maxLength={40} disabled={busy || !!field} onChange={event => setFieldKey(event.target.value)} placeholder="for_example_region" /><span className={styles.hint}>Lowercase letters, numbers and underscores; start with a letter.</span></label>
      <label>Field type<Select value={fieldType} disabled={busy || !!field} onValueChange={value => setFieldType(value as CustomDefinitionResponse["field_type"])}>{types.map(type => <option key={type.value} value={type.value}>{type.label}</option>)}</Select></label>
      <label>Help text<input value={description} maxLength={300} disabled={busy} onChange={event => setDescription(event.target.value)} /></label>
      {fieldType === "select" && <label className={styles.wide}>Choices, one per line<textarea rows={5} value={choices} disabled={busy} onChange={event => setChoices(event.target.value)} /><span className={styles.hint}>Up to 50 choices. A choice in use cannot be removed.</span></label>}
    </div>
    {error && <p role="alert">{error}</p>}
    <div className={styles.actions}><button type="button" className="button primary" disabled={busy || !label.trim() || !fieldKey.trim() || (fieldType === "select" && !choices.trim())} onClick={() => void save()}>{busy ? "Saving…" : field ? "Save field" : "Create field"}</button><button type="button" className="button" disabled={busy} onClick={onCancel}>Cancel</button>{field && <button type="button" className="button" disabled={busy} onClick={() => field.archived ? void save(false) : setConfirmArchive(true)}>{field.archived ? "Restore field" : "Archive field"}</button>}</div>
    {confirmArchive && <div className={styles.confirm}><p>Archive “{field?.label}”? Saved values remain readable. New values cannot be entered until you restore the field.</p><button type="button" className="button danger" disabled={busy} onClick={() => void save(true)}>Confirm archive</button><button type="button" className="button" disabled={busy} onClick={() => setConfirmArchive(false)}>Keep field</button></div>}
  </div>;
}

export function CustomRecordFields(props: { entity: string; recordId: string; canEdit: boolean; onChanged?: () => void }) {
  if (!collections.some(item => item.value === props.entity)) return null;
  return <RecordFieldsLoader key={`${props.entity}:${props.recordId}`} {...props} />;
}

function RecordFieldsLoader({ entity, recordId, canEdit, onChanged }: { entity: string; recordId: string; canEdit: boolean; onChanged?: () => void }) {
  const [data, setData] = useState<CustomRecordResponse | null>(null);
  const [revision, setRevision] = useState(0);
  const [loaded, setLoaded] = useState(-1);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void api<CustomRecordResponse>(`/custom-fields/records/${entity}/${recordId}`, { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) { setData(result); setError(""); } })
      .catch(error => { if (!controller.signal.aborted) setError(reason(error)); })
      .finally(() => { if (!controller.signal.aborted) setLoaded(revision); });
    return () => controller.abort();
  }, [entity, recordId, revision]);
  return <section className={styles.record} aria-label="Record custom fields"><h3>Custom fields</h3>
    {notice && <p role="status">{notice}</p>}
    {loaded !== revision ? <p role="status">Loading custom fields…</p> : error ? <p role="alert">{error}<button className="button" type="button" onClick={() => setRevision(value => value + 1)}>Retry</button></p> : data && data.fields.length > 0 ? <RecordValues key={`${data.version}:${revision}`} data={data} canEdit={canEdit} onEditing={() => setNotice("")} onSaved={value => { setData(value); setNotice("Custom fields saved."); onChanged?.(); }} onReload={() => { setNotice(""); setRevision(value => value + 1); }} /> : <p className={styles.hint}>No custom fields are configured for this record type.</p>}
  </section>;
}

function display(value: string | boolean | null | undefined): string { return value === true ? "Yes" : value === false ? "No" : value ?? "Not set"; }

function RecordValues({ data, canEdit, onSaved, onReload, onEditing }: { data: CustomRecordResponse; canEdit: boolean; onSaved: (data: CustomRecordResponse) => void; onReload: () => void; onEditing: () => void }) {
  const [values, setValues] = useState(data.values);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const retry = useRef<ReturnType<typeof idempotencyRequest> | null>(null);
  const active = data.fields.filter(field => !field.archived);
  const dirty = active.some(field => (values[field.id] ?? null) !== (data.values[field.id] ?? null));
  function update(id: string, value: string | boolean | null) { setValues(current => ({ ...current, [id]: value })); onEditing(); }
  async function save() {
    if (busy || !dirty) return;
    const body = { version: data.version, values: Object.fromEntries(active.map(field => [field.id, values[field.id] ?? null])) };
    retry.current = idempotencyRequest(body, retry.current); setBusy(true); setError("");
    try { const result = await api<CustomRecordResponse>(`/custom-fields/records/${data.entity}/${data.record_id}`, { method: "PATCH", body: JSON.stringify(body), headers: { "Idempotency-Key": retry.current.key } }); setValues(result.values); retry.current = null; onSaved(result); }
    catch (error) { setError(reason(error)); }
    finally { setBusy(false); }
  }
  return <>
    <div className={styles.grid}>{data.fields.map(field => <label key={field.id}>{field.label}{field.archived && <span className={styles.hint}>Archived</span>}
      {!canEdit || field.archived ? <span className={styles.value}>{display(values[field.id])}</span> : field.field_type === "boolean" ? <Select aria-label={field.label} value={values[field.id] === true ? "yes" : values[field.id] === false ? "no" : ""} disabled={busy} onValueChange={value => update(field.id, value === "" ? null : value === "yes")}><option value="">Not set</option><option value="yes">Yes</option><option value="no">No</option></Select> : field.field_type === "select" ? <Select aria-label={field.label} value={String(values[field.id] ?? "")} disabled={busy} onValueChange={value => update(field.id, value || null)}><option value="">Not set</option>{field.options.map(option => <option key={option} value={option}>{option}</option>)}</Select> : <input aria-label={field.label} type={field.field_type === "date" ? "date" : "text"} inputMode={field.field_type === "number" ? "decimal" : undefined} maxLength={field.field_type === "text" ? 2000 : undefined} value={String(values[field.id] ?? "")} disabled={busy} onChange={event => update(field.id, event.target.value || null)} />}
      {field.description && <span className={styles.hint}>{field.description}</span>}{field.field_type === "number" && canEdit && !field.archived && <span className={styles.hint}>Up to 12 integer and 6 decimal digits; no commas.</span>}
    </label>)}</div>
    {canEdit && active.length > 0 && <div className={styles.actions}><button type="button" className="button primary" disabled={busy || !dirty} onClick={() => void save()}>{busy ? "Saving…" : "Save custom fields"}</button><span className={styles.hint}>Saved separately from the record details.</span></div>}
    {error && <div role="alert"><p>{error}</p><button type="button" className="button" disabled={busy} onClick={onReload}>Reload saved values</button></div>}
    {data.history.length > 0 && <details className={styles.history}><summary>Recent custom field changes</summary><ol>{data.history.map((event, index) => <li key={`${event.created_at}:${index}`}><time>{formatTimestamp(event.created_at)}</time>{event.changes.map(change => <p key={change.field_id}><strong>{change.label}</strong>: {display(change.before)} → {display(change.after)}</p>)}</li>)}</ol></details>}
  </>;
}
