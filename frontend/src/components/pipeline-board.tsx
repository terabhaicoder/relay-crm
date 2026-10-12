"use client";

import { useEffect, useState } from "react";
import { api, amount, Row, text } from "@/lib/api/client";
import { Select } from "./ui/select";
import styles from "./pipeline-board.module.css";

export type BoardStage = { id: string; name: string; category: string; color: string; probability: number };
type Totals = { id: string; total: number; amount: string };
export function PipelineBoard({ pipelineId, stages, query, revision, canWrite, onOpen, onCreate, onChanged }: {
  pipelineId: string; stages: BoardStage[]; query: string; revision: number; canWrite: boolean;
  onOpen: (row: Row) => void; onCreate: (stageId: string) => void; onChanged: () => void;
}) {
  const [retry, setRetry] = useState(0);
  const [totals, setTotals] = useState<{ scope: string; items?: Totals[]; error?: string }>({ scope: "" });
  const scope = JSON.stringify([pipelineId, query, revision, retry]);
  useEffect(() => {
    let current = true;
    api<{ stages: Totals[] }>(`/deals/board-summary?${new URLSearchParams({ pipeline_id: pipelineId, q: query })}`)
      .then(data => { if (current) setTotals({ scope, items: data.stages }); })
      .catch((error: Error) => { if (current) setTotals({ scope, error: error.message }); });
    return () => { current = false; };
  }, [pipelineId, query, scope]);
  return <div>
    <p className={styles.note}>Stage totals include every matching deal. Browse each stage independently; move a deal by dragging or using its Move menu.</p>
    {totals.scope === scope && totals.error && <p className="form-error" role="alert">{totals.error} <button className="button subtle" onClick={() => setRetry(retry + 1)}>Retry totals</button></p>}
    <div className={styles.board}>{stages.map(stage => <StageColumn key={`${pipelineId}-${stage.id}`} stage={stage} stages={stages} pipelineId={pipelineId} query={query} revision={revision} canWrite={canWrite} total={totals.scope === scope ? totals.items?.find(item => item.id === stage.id) : undefined} onOpen={onOpen} onCreate={onCreate} onChanged={onChanged}/>)}</div>
  </div>;
}

function StageColumn({ stage, stages, pipelineId, query, revision, canWrite, total, onOpen, onCreate, onChanged }: {
  stage: BoardStage; stages: BoardStage[]; pipelineId: string; query: string; revision: number; canWrite: boolean; total?: Totals;
  onOpen: (row: Row) => void; onCreate: (stageId: string) => void; onChanged: () => void;
}) {
  const [page, setPage] = useState(0);
  const [retry, setRetry] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loss, setLoss] = useState<{ row: Row; stageId: string } | null>(null);
  const [reason, setReason] = useState("");
  const [result, setResult] = useState<{ scope: string; items?: Row[]; total?: number; error?: string }>({ scope: "" });
  const scope = JSON.stringify([pipelineId, stage.id, query, page, revision, retry]);
  useEffect(() => {
    let current = true;
    const params = new URLSearchParams({ pipeline_id: pipelineId, stage_id: stage.id, q: query, limit: "10", offset: String(page * 10), sort: "updated_at", order: "desc" });
    api<{ items: Row[]; total: number }>(`/deals?${params}`).then(data => {
      if (!current) return;
      if (page && !data.items.length && data.total <= page * 10) { setPage(Math.max(0, Math.ceil(data.total / 10) - 1)); return; }
      setResult({ scope, ...data });
    }).catch((error: Error) => { if (current) setResult({ scope, error: error.message }); });
    return () => { current = false; };
  }, [pipelineId, stage.id, query, page, scope]);
  async function move(row: Row, stageId: string, lossReason?: string) {
    if (!canWrite || busy || row.stage_id === stageId) return;
    if (stages.find(item => item.id === stageId)?.category === "lost" && !lossReason) { setLoss({ row, stageId }); setReason(""); return; }
    setBusy(true); setError("");
    try {
      await api(`/deals/${row.id}/stage`, { method: "PATCH", body: JSON.stringify({ stage_id: stageId, version: row.version, reason: lossReason }) });
      setLoss(null); onChanged();
    } catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  }
  const ready = result.scope === scope;
  return <section className={styles.column} aria-label={`${stage.name} deals`} onDragOver={event => { if (canWrite) event.preventDefault(); }} onDrop={event => {
    event.preventDefault(); if (!canWrite || busy) return;
    try { const row = JSON.parse(event.dataTransfer.getData("application/relay-deal")) as Row; if (typeof row.id === "string") void move(row, stage.id); }
    catch { setError("Drag a deal from this board to move it."); }
  }}>
    <header className={styles.header}><div><span className={styles.dot} style={{ background: stage.color || "#36775f" }}/><h2>{stage.name}</h2><span>{total?.total ?? "—"}</span></div><strong>{total ? amount(total.amount) : "Loading total…"}</strong></header>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    {loss && <form className={styles.loss} onSubmit={event => { event.preventDefault(); if (reason.trim()) void move(loss.row, loss.stageId, reason.trim()); }}><label>Why was {text(loss.row.name)} lost?<input required value={reason} onChange={event => setReason(event.target.value)} maxLength={1000}/></label><div><button type="submit" className="button primary" disabled={busy || !reason.trim()}>Confirm lost</button><button type="button" className="button subtle" onClick={() => setLoss(null)}>Cancel</button></div></form>}
    {!ready ? <p role="status" className={styles.empty}>Loading deals…</p> : result.error ? <div role="alert" className={styles.error}>{result.error}<button className="button subtle" onClick={() => setRetry(retry + 1)}>Try again</button></div> : !result.items?.length ? <p className={styles.empty}>No matching deals in this stage.</p> : result.items.map(row => <article key={row.id} className={styles.card} draggable={canWrite && !busy} onDragStart={event => event.dataTransfer.setData("application/relay-deal", JSON.stringify({ id: row.id, name: row.name, version: row.version, stage_id: row.stage_id }))}>
      <button type="button" className={styles.open} onClick={() => onOpen(row)}><span>{text(row.company_name || row.party_name) || "Opportunity"}</span><strong>{text(row.name)}</strong><b>{amount(row.amount)}</b><small>{text(row.expected_close_date).slice(0, 10) || "No close date"}{row.owner_name ? ` · ${text(row.owner_name)}` : ""}</small></button>
      {canWrite && <div className={styles.move}><Select aria-label={`Move ${text(row.name)}`} value="" disabled={busy} onChange={event => { if (event.target.value) void move(row, event.target.value); }}><option value="">Move to stage…</option>{stages.filter(item => item.id !== stage.id).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></div>}
    </article>)}
    {ready && (result.total ?? 0) > 10 && <div className={styles.pager}><button className="button subtle" disabled={!page} onClick={() => setPage(page - 1)} aria-label={`Previous ${stage.name} deals`}>Previous</button><span>{page + 1} / {Math.ceil((result.total ?? 0) / 10)}</span><button className="button subtle" disabled={(page + 1) * 10 >= (result.total ?? 0)} onClick={() => setPage(page + 1)} aria-label={`Next ${stage.name} deals`}>Next</button></div>}
    {canWrite && stage.category === "open" && <button className={styles.add} onClick={() => onCreate(stage.id)}>+ Add deal</button>}
  </section>;
}
