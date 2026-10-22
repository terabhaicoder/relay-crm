"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { amount, api, formatTimestamp, idempotencyRequest, text, type Row, type User } from "@/lib/api/client";
import type { QuoteList, QuoteResponse } from "@/lib/api/schema";
import { Select } from "./ui/select";
import styles from "./quotations.module.css";

export type Quotation = QuoteResponse;
type EditableLine = { key: string; description: string; quantity: string; unit_price: string };
type RequestKey = { fingerprint: string; key: string };
type Decision = "issue" | "accept" | "decline";

function printable(quote: Quotation) {
  const popup = window.open("", "_blank", "width=900,height=800");
  if (!popup) throw new Error("Allow popups to open the printable quotation.");
  popup.opener = null;
  popup.document.title = quote.name;
  const style = popup.document.createElement("style");
  style.textContent = "body{font:15px Georgia,serif;max-width:850px;margin:50px;color:#173a30}h1{font-size:32px}table{width:100%;border-collapse:collapse;margin:30px 0}th,td{text-align:left;padding:12px 8px;border-bottom:1px solid #ccc}p{white-space:pre-wrap}.total{font-size:24px}small{font:12px Arial,sans-serif;color:#666}@media print{body{margin:20px}}";
  popup.document.head.append(style);
  const add = (tag: string, content: string) => {
    const element = popup.document.createElement(tag); element.textContent = content; popup.document.body.append(element); return element;
  };
  add("small", `RELAY · QUOTATION · ${quote.status.toUpperCase()} · ${quote.id}`);
  add("h1", quote.name); add("p", `Prepared for ${quote.customer_name}${quote.contact_name ? `\n${quote.contact_name}` : ""}`);
  add("p", `Deal: ${quote.deal_name}\nValid until: ${quote.valid_until || "Not specified"}`);
  const table = popup.document.createElement("table");
  const header = table.createTHead().insertRow();
  for (const label of ["Description", "Quantity", "Unit price (INR)", "Amount (INR)"]) { const cell = popup.document.createElement("th"); cell.textContent = label; header.append(cell); }
  const body = table.createTBody();
  for (const line of quote.lines) { const row = body.insertRow(); for (const value of [line.description, line.quantity, line.unit_price, line.amount]) row.insertCell().textContent = value; }
  popup.document.body.append(table);
  add("p", `Subtotal: ${amount(quote.subtotal)}\nDiscount: ${amount(quote.discount)}`);
  add("h2", `Total: ${amount(quote.total)}`); add("small", "Commercial estimate. Tax is excluded. This is not an invoice or payment receipt.");
  if (quote.terms) { add("h2", "Terms"); add("p", quote.terms); }
  if (quote.decision_note) { add("h2", "Recorded customer decision"); add("p", quote.decision_note); }
  add("small", "Issued means the terms are locked in Relay. It does not confirm delivery to the customer.");
  popup.document.close(); popup.focus(); popup.print();
}

function QuoteEditor({ initial, dealId, onSaved, onCancel }: { initial?: Quotation; dealId?: string; onSaved: (quote: Quotation) => void; onCancel: () => void }) {
  const [name, setName] = useState(initial?.name ?? "");
  const [validUntil, setValidUntil] = useState(initial?.valid_until ?? "");
  const [terms, setTerms] = useState(initial?.terms ?? "");
  const [discount, setDiscount] = useState(initial?.discount ?? "0.00");
  const [lines, setLines] = useState<EditableLine[]>(initial?.lines.map(line => ({ ...line, key: line.id })) ?? [{ key: "first", description: "", quantity: "1", unit_price: "" }]);
  const [deal, setDeal] = useState<Row | null>(null);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<{ query: string; rows: Row[]; total: number } | null>(null);
  const [error, setError] = useState("");
  const [searchError, setSearchError] = useState("");
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  const request = useRef<RequestKey | null>(null);
  const sourceDeal = initial?.deal_id ?? dealId;

  useEffect(() => {
    if (!sourceDeal) return;
    const controller = new AbortController();
    api<Row>(`/deals/${encodeURIComponent(sourceDeal)}`, { signal: controller.signal })
      .then(setDeal).catch((failure: Error) => { if (!controller.signal.aborted) setError(failure.message); });
    return () => controller.abort();
  }, [sourceDeal, retry]);
  useEffect(() => {
    if (deal || search.trim().length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setSearchError("");
      api<{ items: Row[]; total: number }>(`/deals?status=open&q=${encodeURIComponent(search.trim())}&limit=10`, { signal: controller.signal })
        .then(data => setResults({ query: search, rows: data.items, total: data.total }))
        .catch((failure: Error) => { if (!controller.signal.aborted) setSearchError(failure.message); });
    }, 200);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [deal, search, retry]);

  function updateLine(key: string, field: keyof EditableLine, value: string) {
    setLines(current => current.map(line => line.key === key ? { ...line, [field]: value } : line));
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (!deal) { setError("Select an accessible open deal first."); return; }
    setBusy(true); setError("");
    const fields = { name, valid_until: validUntil || null, terms, discount,
      lines: lines.map(({ description, quantity, unit_price }) => ({ description, quantity, unit_price })) };
    const body = initial ? { ...fields, version: initial.version } : { ...fields, deal_id: deal.id };
    request.current = idempotencyRequest(body, request.current);
    try {
      const saved = await api<Quotation>(initial ? `/quotations/${initial.id}` : "/quotations", {
        method: initial ? "PATCH" : "POST", body: JSON.stringify(body), headers: { "Idempotency-Key": request.current.key },
      });
      onSaved(saved);
    } catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  }
  return <form className={styles.editor} onSubmit={event => void submit(event)} aria-label={initial ? "Edit quotation" : "New quotation"}>
    <header><h2>{initial ? "Refine your quotation" : "A clear offer, ready to share."}</h2><p>Link an open deal, add the work and save a draft. Totals are calculated on save.</p></header>
    {error && <div className={styles.error} role="alert">{error}{sourceDeal && !deal && <button type="button" className="button subtle" onClick={() => { setError(""); setRetry(value => value + 1); }}>Retry deal</button>}</div>}
    <fieldset disabled={busy}>
      {deal ? <div className={styles.deal}><span>Linked deal</span><strong>{text(deal.name)}</strong><Link href={`/deals?id=${deal.id}`}>View deal</Link>{!initial && !dealId && <button type="button" className="button subtle" onClick={() => { setDeal(null); setSearch(""); }}>Change deal</button>}</div> : <label>Find an open deal<input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search by deal name…" autoComplete="off" /></label>}
      {!deal && search.trim().length >= 2 && <div className={styles.searchResults}>
        {searchError ? <p role="alert">{searchError}<button type="button" onClick={() => setRetry(value => value + 1)}>Retry search</button></p> : results?.query !== search ? <p role="status">Finding deals…</p> : results.rows.length ? <>{results.rows.map(row => <button type="button" key={row.id} onClick={() => { setDeal(row); if (!name) setName(`${text(row.name)} quotation`); }}>{text(row.name)} <span>{amount(row.amount)}</span></button>)}{results.total > 10 && <p>Refine your search to see more matches.</p>}</> : <p>No open deals match. Create a deal with a company or contact first.</p>}
      </div>}
      <div className={styles.fields}><label>Quotation title<input required maxLength={200} value={name} onChange={event => setName(event.target.value)} /></label><label>Valid until<input type="date" value={validUntil} onChange={event => setValidUntil(event.target.value)} /></label></div>
      <div className={styles.lineHeading}><h3>Products & services</h3><span>INR · tax excluded</span></div>
      <div className={styles.lines}>{lines.map((line, index) => <div className={styles.line} key={line.key}>
        <label>Description {index + 1}<input required maxLength={500} value={line.description} onChange={event => updateLine(line.key, "description", event.target.value)} placeholder="Service or product" /></label>
        <label>Quantity {index + 1}<input required type="number" min="0.001" max="999999.999" step="0.001" value={line.quantity} onChange={event => updateLine(line.key, "quantity", event.target.value)} /></label>
        <label>Unit price {index + 1}<input required type="number" min="0" max="999999.9999" step="0.0001" value={line.unit_price} onChange={event => updateLine(line.key, "unit_price", event.target.value)} /></label>
        <button type="button" className="button subtle" disabled={lines.length === 1} aria-label={`Remove line ${index + 1}`} onClick={() => setLines(current => current.filter(item => item.key !== line.key))}>Remove</button>
      </div>)}</div>
      <button type="button" className="button subtle" disabled={lines.length >= 100} onClick={() => setLines(current => [...current, { key: crypto.randomUUID(), description: "", quantity: "1", unit_price: "" }])}>+ Add line</button>
      <div className={styles.fields}><label>Discount (INR)<input type="number" min="0" step="0.01" required value={discount} onChange={event => setDiscount(event.target.value)} /></label><p className={styles.hint}>Each line rounds to paise. The discount is subtracted from the rounded subtotal.</p></div>
      <label>Terms<textarea rows={3} maxLength={10000} value={terms} onChange={event => setTerms(event.target.value)} placeholder="Scope, delivery, payment terms and exclusions…" /></label>
    </fieldset>
    <footer className={styles.actions}><button type="button" className="button subtle" disabled={busy} onClick={onCancel}>Cancel</button><button type="submit" className="button primary" disabled={busy || !deal}>{busy ? "Saving…" : "Save draft"}</button></footer>
  </form>;
}

export function Quotations({ dealId, canEdit: editPermission, onChanged }: { dealId?: string; canEdit?: boolean; onChanged?: () => void }) {
  const params = useSearchParams();
  const [roleCanEdit, setCanEdit] = useState(false);
  const canEdit = editPermission ?? roleCanEdit;
  const [showAllDeals, setShowAllDeals] = useState(false);
  const filterDeal = showAllDeals ? "" : dealId ?? params.get("deal_id") ?? "";
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<{ key: string; data?: QuoteList; error?: string } | null>(null);
  const [selectedId, setSelectedId] = useState(params.get("id") ?? "");
  const [detail, setDetail] = useState<{ key: string; data?: Quotation; error?: string } | null>(null);
  const [editor, setEditor] = useState<"new" | "edit" | null>(params.get("new") === "1" ? "new" : null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [note, setNote] = useState("");
  const [closeDeal, setCloseDeal] = useState(false);
  const [linkedDeal, setLinkedDeal] = useState<Row | null>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<{ error: boolean; message: string } | null>(null);
  const request = useRef<RequestKey | null>(null);
  const listKey = `${filterDeal}/${query}/${status}/${offset}/${revision}`;
  const detailKey = `${selectedId}/${revision}`;
  const data = result?.key === listKey ? result.data : undefined;
  const quote = detail?.key === detailKey ? detail.data : undefined;

  useEffect(() => {
    if (editPermission !== undefined) return;
    const controller = new AbortController();
    api<User>("/auth/me", { signal: controller.signal }).then(user => setCanEdit(!["Read-only", "Read-only/CA", "Viewer"].includes(user.role)))
      .catch((failure: Error) => { if (!controller.signal.aborted) setFeedback({ error: true, message: failure.message }); });
    return () => controller.abort();
  }, [editPermission]);
  useEffect(() => {
    const controller = new AbortController();
    const parameters = new URLSearchParams({ q: query, limit: "20", offset: String(offset) });
    if (status) parameters.set("status", status); if (filterDeal) parameters.set("deal_id", filterDeal);
    api<QuoteList>(`/quotations?${parameters}`, { signal: controller.signal })
      .then(value => setResult({ key: listKey, data: value }))
      .catch((failure: Error) => { if (!controller.signal.aborted) setResult({ key: listKey, error: failure.message }); });
    return () => controller.abort();
  }, [filterDeal, query, status, offset, listKey]);
  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    api<Quotation>(`/quotations/${encodeURIComponent(selectedId)}`, { signal: controller.signal })
      .then(value => setDetail({ key: detailKey, data: value }))
      .catch((failure: Error) => { if (!controller.signal.aborted) setDetail({ key: detailKey, error: failure.message }); });
    return () => controller.abort();
  }, [selectedId, detailKey]);
  useEffect(() => {
    if (!quote || decision !== "accept") return;
    const controller = new AbortController();
    api<Row>(`/deals/${quote.deal_id}`, { signal: controller.signal }).then(setLinkedDeal)
      .catch((failure: Error) => { if (!controller.signal.aborted) setFeedback({ error: true, message: failure.message }); });
    return () => controller.abort();
  }, [quote, decision]);

  function saved(value: Quotation) { setSelectedId(value.id); setEditor(null); setDecision(null); setRevision(current => current + 1); setFeedback({ error: false, message: "Quotation draft saved." }); onChanged?.(); }
  async function confirm(event: FormEvent) {
    event.preventDefault(); if (!quote || !decision || busy) return;
    setBusy(true); setFeedback(null);
    const body = { version: quote.version, note, close_deal: decision === "accept" && closeDeal, deal_version: decision === "accept" && closeDeal ? Number(linkedDeal?.version) : null };
    request.current = idempotencyRequest({ action: decision, id: quote.id, ...body }, request.current);
    try {
      await api<Quotation>(`/quotations/${quote.id}/${decision}`, { method: "POST", body: JSON.stringify(body), headers: { "Idempotency-Key": request.current.key } });
      setFeedback({ error: false, message: decision === "issue" ? "Quotation issued. Its terms are now locked; delivery is not confirmed." : decision === "accept" ? closeDeal ? "Customer acceptance recorded and linked deal marked won." : "Customer acceptance recorded. The deal remains unchanged." : "Customer decline recorded." });
      setDecision(null); setRevision(value => value + 1); request.current = null; onChanged?.();
    } catch (failure) { setFeedback({ error: true, message: (failure as Error).message }); }
    finally { setBusy(false); }
  }
  function startDecision(value: Decision) { setDecision(value); setNote(""); setCloseDeal(false); setLinkedDeal(null); setFeedback(null); }

  return <section className={styles.page} aria-label="Quotations workspace">
    <header className={styles.header}><div><h2>Make the next step clear.</h2><p>Prepare commercial terms, keep a permanent issued copy, and record the customer’s decision.</p></div>{canEdit && !editor && <button type="button" className="button primary" onClick={() => { setEditor("new"); setFeedback(null); }}>New quotation</button>}</header>
    {feedback && <p className={feedback.error ? styles.error : styles.success} role={feedback.error ? "alert" : "status"}>{feedback.message}</p>}
    {editor && canEdit && <QuoteEditor key={editor === "edit" ? `${quote?.id}/${quote?.version}` : `new/${filterDeal}`} initial={editor === "edit" ? quote : undefined} dealId={filterDeal || undefined} onSaved={saved} onCancel={() => setEditor(null)} />}
    {(!editor || !canEdit) && <div className={styles.layout}>
      <aside className={styles.collection} aria-label="Quotation list">
        <div className={styles.filters}><label>Search quotations<input type="search" value={query} onChange={event => { setQuery(event.target.value); setOffset(0); }} placeholder="Quotation title…" /></label><label>Quotation status<Select value={status} onValueChange={value => { setStatus(value); setOffset(0); }}><option value="">All statuses</option><option value="draft">Draft</option><option value="issued">Issued</option><option value="accepted">Accepted</option><option value="declined">Declined</option></Select></label></div>
        {filterDeal && <p className={styles.hint}>Showing quotations for one deal. <button type="button" onClick={() => { setShowAllDeals(true); setOffset(0); }}>Show all</button></p>}
        {result?.key !== listKey && <p role="status">Loading quotations…</p>}
        {result?.key === listKey && result.error && <p role="alert">{result.error}<button type="button" className="button subtle" onClick={() => setRevision(value => value + 1)}>Retry quotations</button></p>}
        {data && <><p className={styles.count}>{data.total} quotation{data.total === 1 ? "" : "s"}</p>{data.items.length ? <ul className={styles.quoteList}>{data.items.map(item => <li key={item.id}><button type="button" aria-pressed={selectedId === item.id} onClick={() => { setSelectedId(item.id); setDecision(null); setFeedback(null); }}><span><strong>{item.name}</strong><small>{item.customer_name}</small></span><span><strong>{amount(item.total)}</strong><small className={styles.status}>{item.status}</small></span></button></li>)}</ul> : <div className={styles.empty}><h3>{query || status ? "No quotations match" : "Your next agreement starts here"}</h3><p>{query || status ? "Try a different search or status." : "Create a quotation from an open deal to keep scope, pricing and the customer’s decision together."}</p></div>}
        {data.total > 20 && <div className={styles.pager}><button className="button subtle" disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - 20))}>Previous</button><span>{offset + 1}–{Math.min(offset + 20, data.total)}</span><button className="button subtle" disabled={offset + 20 >= data.total} onClick={() => setOffset(value => value + 20)}>Next</button></div>}</>}
      </aside>
      <article className={styles.document} aria-label="Quotation details">
        {!selectedId && <div className={styles.empty}><h2>Choose a quotation</h2><p>Review its commercial terms and follow the decision from draft to agreement.</p></div>}
        {selectedId && detail?.key !== detailKey && <p role="status">Loading quotation…</p>}
        {detail?.key === detailKey && detail.error && <p role="alert">{detail.error}<button type="button" className="button subtle" onClick={() => setRevision(value => value + 1)}>Reload quotation</button></p>}
        {quote && <><header className={styles.documentHeader}><span className={styles.eyebrow}>QUOTATION · {quote.status.toUpperCase()}</span><h2>{quote.name}</h2><p>Prepared for <strong>{quote.customer_name}</strong>{quote.contact_name && ` · ${quote.contact_name}`}</p><Link href={`/deals?id=${quote.deal_id}`}>{quote.deal_name} ↗</Link><p className={styles.hint}>Valid until {quote.valid_until || "not specified"} · INR · tax excluded</p></header>
          <div className={styles.tableScroll}><table><thead><tr><th>Description</th><th>Quantity</th><th>Unit price</th><th>Amount</th></tr></thead><tbody>{quote.lines.map(line => <tr key={line.id}><td>{line.description}</td><td>{line.quantity}</td><td>₹{line.unit_price}</td><td>{amount(line.amount)}</td></tr>)}</tbody></table></div>
          <dl className={styles.totals}><div><dt>Subtotal</dt><dd>{amount(quote.subtotal)}</dd></div><div><dt>Discount</dt><dd>− {amount(quote.discount)}</dd></div><div className={styles.grandTotal}><dt>Total</dt><dd>{amount(quote.total)}</dd></div></dl>
          <p className={styles.hint}>Commercial estimate. Tax is excluded. This is not an invoice or a payment receipt.</p>
          {quote.terms && <section className={styles.terms}><h3>Terms</h3><p>{quote.terms}</p></section>}
          {quote.decision_note && <section className={styles.terms}><h3>Recorded customer decision</h3><p>{quote.decision_note}</p><small>{formatTimestamp(quote.decided_at)}</small></section>}
          <div className={styles.actions}><button className="button subtle" onClick={() => { try { printable(quote); } catch (failure) { setFeedback({ error: true, message: (failure as Error).message }); } }}>Print / Save PDF</button><button className="button subtle" disabled={busy} onClick={() => { setDecision(null); setRevision(value => value + 1); }}>Refresh</button>{canEdit && !decision && quote.status === "draft" && <><button className="button subtle" onClick={() => setEditor("edit")}>Edit draft</button><button className="button primary" onClick={() => startDecision("issue")}>Issue quotation</button></>}{canEdit && !decision && quote.status === "issued" && <><button className="button subtle" onClick={() => startDecision("decline")}>Record decline</button><button className="button primary" onClick={() => startDecision("accept")}>Record acceptance</button></>}</div>
          {decision && <form className={styles.decision} onSubmit={event => void confirm(event)} aria-label="Quotation decision"><h3>{decision === "issue" ? "Lock this offer’s terms?" : decision === "accept" ? "Record customer acceptance" : "Record customer decline"}</h3><p>{decision === "issue" ? "Issuing creates a permanent commercial record. Share the printable copy yourself; Relay does not send it." : "Record a real customer decision and its reference. This is an internal record, not an electronic signature."}</p>{decision !== "issue" && <label>Decision note<textarea required rows={3} maxLength={2000} value={note} disabled={busy} onChange={event => setNote(event.target.value)} placeholder="Who confirmed, when, and where the evidence is recorded…" /></label>}{decision === "accept" && <><label className={styles.checkbox}><input type="checkbox" checked={closeDeal} disabled={busy || !linkedDeal || linkedDeal.status !== "open"} onChange={event => setCloseDeal(event.target.checked)} />Also mark the linked deal won at {amount(quote.total)}</label>{!linkedDeal ? <p role="status">Checking linked deal…</p> : <p className={styles.hint}>Current deal: {text(linkedDeal.status)} · {amount(linkedDeal.amount)}. {closeDeal ? "Acceptance and the updated deal amount will save together." : "Leave unchecked to keep the deal unchanged."}</p>}</>}<div className={styles.actions}><button type="button" className="button subtle" disabled={busy} onClick={() => setDecision(null)}>Cancel</button><button type="submit" className="button primary" disabled={busy || (closeDeal && !linkedDeal)}>{busy ? "Saving…" : decision === "issue" ? "Confirm issue" : decision === "accept" ? "Confirm acceptance" : "Confirm decline"}</button></div></form>}
          <section className={styles.history}><h3>Quotation history</h3><p className={styles.hint}>Most recent 100 events. Issued does not confirm delivery.</p><ol>{quote.events.map((event, index) => <li key={`${event.created_at}/${index}`}><span>{event.action}{event.changes.deal_closed ? " · deal marked won" : ""}</span><time>{formatTimestamp(event.created_at)}</time></li>)}</ol></section>
        </>}
      </article>
    </div>}
  </section>;
}

export default Quotations;
