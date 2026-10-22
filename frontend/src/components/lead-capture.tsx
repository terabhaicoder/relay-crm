"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, formatTimestamp, idempotencyRequest, type User } from "@/lib/api/client";
import styles from "./lead-capture.module.css";

type Capture = { id: string; name: string; title: string; description: string; source: string; enabled: boolean; owner_ids: string[]; version: number; submissions: number; new_leads: number; duplicates: number };
type Submission = { id: string; lead_id: string; name: string; message: string; duplicate: boolean; created_at: string };
const blank = { name: "", title: "Let’s talk about your business", description: "Tell us what you need. Our team will get in touch.", source: "Website", enabled: true, owner_ids: [] as string[] };

export function LeadCaptureSettings({ canManage }: { canManage: boolean }) {
  const [forms, setForms] = useState<Capture[]>([]);
  const [team, setTeam] = useState<(User & { is_active?: boolean })[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [editor, setEditor] = useState<Partial<Capture> | null>(null);
  const [selected, setSelected] = useState<Capture | null>(null);
  const [receiptPage, setReceiptPage] = useState(0);
  const [receipts, setReceipts] = useState<{items: Submission[]; total: number} | null>(null);
  const [receiptError, setReceiptError] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const retry = useRef<ReturnType<typeof idempotencyRequest> | null>(null);

  useEffect(() => {
    if (!canManage) return;
    const controller = new AbortController();
    void Promise.all([api<{items:Capture[]; total:number}>(`/capture-forms?limit=20&offset=${page * 20}`, {signal:controller.signal}), api<(User & {is_active?:boolean})[]>("/team", {signal:controller.signal})]).then(([data, people]) => {
      if (!controller.signal.aborted) { setForms(data.items); setTotal(data.total); setTeam(people); setError(""); }
    }).catch(reason => { if (!controller.signal.aborted) setError((reason as Error).message); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [canManage, page, revision]);

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    void api<{items:Submission[]; total:number}>(`/capture-forms/${selected.id}/submissions?limit=20&offset=${receiptPage * 20}`, {signal:controller.signal}).then(result => { if (!controller.signal.aborted) {setReceipts(result); setReceiptError("");} }).catch(reason => { if (!controller.signal.aborted) setReceiptError((reason as Error).message); });
    return () => controller.abort();
  }, [selected, receiptPage, revision]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editor || busy) return;
    const form = new FormData(event.currentTarget);
    const body = {name:form.get("name"), title:form.get("title"), description:form.get("description"), source:form.get("source"), enabled:form.has("enabled"), owner_ids:form.getAll("owners"), ...(editor.id ? {version:editor.version} : {})};
    retry.current = idempotencyRequest(body, retry.current);
    setBusy(true); setError(""); setNotice("");
    try {
      await api(editor.id ? `/capture-forms/${editor.id}` : "/capture-forms", {method:editor.id ? "PATCH" : "POST", headers:{"Idempotency-Key":retry.current.key}, body:JSON.stringify(body)});
      setEditor(null); retry.current = null; setRevision(n => n+1); setNotice("Lead form saved. New inquiries will use this routing.");
    } catch (reason) { setError((reason as Error).message); } finally { setBusy(false); }
  }

  if (!canManage) return <p className="muted">Ask a workspace manager to configure lead capture and routing.</p>;
  return <div className={styles.workspace}>
    <header className={styles.header}><div><h2>Lead capture</h2><p className="muted">An inquiry becomes a lead, gets an owner, and starts your follow-up workflows.</p></div><button className="button primary" onClick={() => { setEditor({...blank}); setError(""); setNotice(""); }}>Create lead form</button></header>
    <div className={styles.actions}><button className="button secondary" onClick={() => { setLoading(true); setError(""); setReceiptError(""); setReceipts(null); setRevision(n=>n+1); }}>Refresh forms & inquiries</button></div>
    <div className={styles.flow}><span>01 · Capture inquiry</span><span>02 · Assign owner</span><span>03 · Start follow-up</span></div>
    <p className="muted">Forms run on this local CRM. Duplicate email or phone inquiries keep the existing lead and owner; every new inquiry is retained below.</p>
    {error && <div className="form-error" role="alert">{error}</div>}{notice && <p role="status" className={styles.notice}>{notice}</p>}
    {editor && <form className={styles.editor} onSubmit={save} key={editor.id ?? "new"}><h3>{editor.id ? "Edit lead form" : "New lead form"}</h3><div className={styles.grid}><label>Internal form name<input name="name" defaultValue={editor.name} maxLength={100} required/></label><label>Lead source<input name="source" defaultValue={editor.source} maxLength={100} required/></label></div><label>Public heading<input name="title" defaultValue={editor.title} maxLength={160} required/></label><label>Introduction<textarea name="description" defaultValue={editor.description} maxLength={2000} rows={2}/></label><fieldset><legend>Assignment rotation</legend><p className="muted">New leads rotate through selected teammates. Leave empty to assign to the form creator. Inactive teammates are skipped.</p><div className={styles.owners}>{team.filter(member => member.is_active !== false && !["Read-only", "Viewer", "Read-only/CA"].includes(member.role)).map(member => <label key={member.id}><input type="checkbox" name="owners" value={member.id} defaultChecked={editor.owner_ids?.includes(member.id)}/>{member.name}<small>{member.role}</small></label>)}</div></fieldset><label className={styles.check}><input type="checkbox" name="enabled" defaultChecked={editor.enabled}/>Accept inquiries</label><div className={styles.actions}><button type="button" className="button secondary" disabled={busy} onClick={() => setEditor(null)}>Cancel</button><button className="button primary" disabled={busy}>{busy ? "Saving…" : "Save lead form"}</button></div></form>}
    {loading ? <p role="status">Loading lead forms…</p> : forms.length === 0 && !error ? <div className={styles.empty}><h3>A clear entry point for new business</h3><p>Create your first form, open its local link, and submit an inquiry to see it land in Leads.</p></div> : <div className={styles.cards}>{forms.map(form => <article className={styles.card} key={form.id}><div className={styles.header}><h3>{form.name}</h3><span className={styles.status}>{form.enabled ? "Accepting inquiries" : "Paused"}</span></div><p>{form.title}</p><div className={styles.metrics}><span><b>{form.submissions}</b> inquiries</span><span><b>{form.new_leads}</b> new leads</span><span><b>{form.duplicates}</b> existing leads</span></div><p className="muted">{form.source} · {form.owner_ids.length ? `${form.owner_ids.length} teammate${form.owner_ids.length === 1 ? "" : "s"} in rotation` : "Assigned to form creator"}</p><div className={styles.actions}><Link href={`/capture/${form.id}`} target="_blank" className="button secondary">Open local form ↗</Link><button className="button subtle" onClick={() => { setSelected(form); setReceiptPage(0); setReceipts(null); setReceiptError(""); setRevision(n=>n+1); }}>View inquiries</button><button className="button subtle" onClick={() => { setEditor(form); setError(""); }}>Edit form</button></div></article>)}</div>}
    {total > 20 && <div className={styles.actions}><button className="button secondary" disabled={page === 0} onClick={() => {setLoading(true); setPage(n=>n-1);}}>Previous forms</button><span>{page * 20 + 1}–{Math.min((page+1)*20,total)} of {total}</span><button className="button secondary" disabled={(page+1)*20 >= total} onClick={() => {setLoading(true); setPage(n=>n+1);}}>Next forms</button></div>}
    {selected && <section className={styles.editor}><div className={styles.header}><h3>{selected.name} · Inquiries</h3><button className="button subtle" onClick={()=>setSelected(null)}>Close inquiries</button></div>{receiptError ? <p role="alert">{receiptError} Use Refresh forms & inquiries to retry.</p> : !receipts ? <p role="status">Loading inquiries…</p> : !receipts.total ? <p>No inquiries yet.</p> : <>{receipts.items.map(receipt=><article className={styles.receipt} key={receipt.id}><div className={styles.header}><Link href={`/leads?id=${receipt.lead_id}`}>{receipt.name}</Link><span>{receipt.duplicate ? "Existing lead" : "New lead"}</span></div><p>{receipt.message || "No message provided."}</p><small>{formatTimestamp(receipt.created_at)}</small></article>)}<div className={styles.actions}><button className="button secondary" disabled={!receiptPage} onClick={()=>{setReceipts(null);setReceiptPage(n=>n-1);}}>Previous inquiries</button><span>{receiptPage*20+1}–{Math.min((receiptPage+1)*20,receipts.total)} of {receipts.total}</span><button className="button secondary" disabled={(receiptPage+1)*20>=receipts.total} onClick={()=>{setReceipts(null);setReceiptPage(n=>n+1);}}>Next inquiries</button></div></>}</section>}
    <Link className="button subtle" href="/automations">Configure follow-up automations →</Link>
  </div>;
}

export function PublicLeadForm({ formId }: { formId: string }) {
  const [form, setForm] = useState<{title:string;description:string;organization:string} | null>(null);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const retry = useRef<ReturnType<typeof idempotencyRequest> | null>(null);
  useEffect(()=>{const controller=new AbortController(); void api<{title:string;description:string;organization:string}>(`/public/forms/${formId}`, {signal:controller.signal}).then(setForm).catch(reason=>{if(!controller.signal.aborted)setError((reason as Error).message);});return()=>controller.abort();},[formId]);
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();if(busy)return;const data=new FormData(event.currentTarget);const body={name:data.get("name"),email:data.get("email"),phone:data.get("phone"),company:data.get("company"),message:data.get("message"),consent:data.has("consent")};retry.current=idempotencyRequest(body,retry.current);setBusy(true);setError("");try{await api(`/public/forms/${formId}`,{method:"POST",headers:{"Idempotency-Key":retry.current.key},body:JSON.stringify(body)});setSent(true);}catch(reason){setError((reason as Error).message);}finally{setBusy(false);}}
  return <main className={styles.publicPage}><div className={styles.publicCard}><div className={styles.wordmark}><span>r</span> Relay</div>{error&&<p className="form-error" role="alert">{error}</p>}{sent?<div role="status"><h1>Thank you for reaching out.</h1><p>Your inquiry has been received by {form?.organization}. Their team can follow up using the details you shared.</p></div>:!form?(!error&&<p role="status">Loading inquiry form…</p>):<><p className={styles.eyebrow}>{form.organization}</p><h1>{form.title}</h1><p className={styles.intro}>{form.description}</p><form onSubmit={submit}><div className={styles.grid}><label>Your name<input name="name" autoComplete="name" maxLength={255} required/></label><label>Work email<input name="email" type="email" autoComplete="email" maxLength={255} required/></label><label>Company<input name="company" autoComplete="organization" maxLength={255}/></label><label><span>Phone <small>(optional)</small></span><input name="phone" type="tel" autoComplete="tel" placeholder="+91 98765 43210" maxLength={40}/></label></div><label>How can we help?<textarea name="message" maxLength={4000} rows={4}/></label><label className={styles.check}><input name="consent" type="checkbox" required/>I agree to be contacted about this inquiry.</label><button className="button primary" disabled={busy}>{busy?"Submitting…":"Send inquiry"}</button></form><p className={styles.footnote}>Your details are shared with {form.organization} for this inquiry.</p></>}</div></main>;
}
