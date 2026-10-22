"use client";

import { useEffect, useState } from "react";
import { api, text, type Row } from "@/lib/api/client";
import { Select } from "./ui/select";

export function EngagementTemplatePicker({ entity, recordId, initialTemplate = "", onApply }: {
  entity: string; recordId: string; initialTemplate?: string;
  onApply: (content: { subject: string; body: string; recipient?: string }) => void;
}) {
  const [templates, setTemplates] = useState<Row[]>([]);
  const [selected, setSelected] = useState(initialTemplate);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api<{ items: Row[] }>("/email/templates", { signal: controller.signal })
      .then(result => { setTemplates(result.items); setLoaded(true); setError(""); })
      .catch((failure: Error) => { if (!controller.signal.aborted) { setError(failure.message); setLoaded(true); } });
    return () => controller.abort();
  }, [retry]);
  async function apply() {
    const template = templates.find(item => item.id === selected);
    if (!template || busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const record = entity && recordId ? await api<Row>(`/${entity}/${encodeURIComponent(recordId)}`) : null;
      const variables: Record<string, string> = { name: text(record?.name), email: text(record?.email), company: text(record?.company || (entity === "parties" ? record?.name : "")) };
      const render = (value: unknown) => text(value).replace(/\{\{\s*(name|email|company)\s*\}\}/g, (original, key: string) => variables[key] || original);
      const subject = render(template.subject), body = render(template.body);
      onApply({ subject, body, ...(variables.email ? { recipient: variables.email } : {}) });
      setNotice(/\{\{[^}]+\}\}/.test(subject + body) ? "Template applied. Review and replace the remaining placeholders before saving." : "Template applied. Review the recipient and message before saving your draft.");
    } catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  }
  return <section className="context-action" aria-label="Apply email template">
    <h3>Start from a template</h3>
    <p>Use the linked record for name, email and company placeholders. Applying replaces the subject and message; saving keeps this as an unsent draft.</p>
    {!loaded ? <p role="status">Loading templates…</p> : <>
      <label>Template<Select aria-label="Email template" value={selected} disabled={busy} onChange={event => setSelected(event.target.value)}><option value="">Choose a template</option>{templates.map(template => <option key={template.id} value={template.id}>{text(template.name)}</option>)}</Select></label>
      {!templates.length && !error && <p>No templates yet. Create one in the Email workspace.</p>}
      <button className="button secondary" type="button" disabled={busy || !selected || !templates.some(item => item.id === selected)} onClick={() => void apply()}>{busy ? "Applying…" : "Apply template"}</button>
    </>}
    {error && <p role="alert">{error} <button className="button subtle" type="button" onClick={() => { setLoaded(false); setRetry(value => value + 1); }}>Retry templates</button></p>}
    {notice && <p role="status">{notice}</p>}
  </section>;
}
