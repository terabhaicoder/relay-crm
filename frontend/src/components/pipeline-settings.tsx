"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, idempotencyRequest } from "@/lib/api/client";
import { Select } from "./ui/select";
import { Icon } from "./icon";
import styles from "./pipeline-settings.module.css";

type Stage = { id?: string; name: string; probability: number; category: "open" | "won" | "lost"; key?: string };
type Pipeline = { id: string; name: string; stages: Stage[] };
export function PipelineSettings({ onChanged, canWrite = true }: { onChanged?: () => void; canWrite?: boolean }) {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selected, setSelected] = useState("");
  const [name, setName] = useState("");
  const [stages, setStages] = useState<Stage[]>([]);
  const [creating, setCreating] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0);
  const requestKey = useRef<ReturnType<typeof idempotencyRequest> | null>(null);
  function adopt(pipeline: Pipeline) {
    setSelected(pipeline.id); setName(pipeline.name);
    setStages(pipeline.stages.map(stage => ({ ...stage, key: stage.id ?? crypto.randomUUID() })));
    setCreating(false); setDirty(false); setError("");
  }
  useEffect(() => {
    const controller = new AbortController();
    void api<{ items: Pipeline[] }>("/pipelines", { signal: controller.signal }).then(result => {
      if (controller.signal.aborted) return;
      setPipelines(result.items); if (result.items[0]) adopt(result.items[0]);
    }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Couldn't load pipelines. Please retry."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [revision]);
  function startNew() {
    setCreating(true); setSelected(""); setName("");
    setStages(["Qualified", "Discovery", "Proposal", "Negotiation"].map((stageName, index) => ({ key: crypto.randomUUID(), name: stageName, probability: (index + 1) * 20, category: "open" })));
    setDirty(false); setNotice(""); setError(""); requestKey.current = null;
  }
  function change(index: number, patch: Partial<Stage>) {
    setStages(current => current.map((stage, position) => position === index ? { ...stage, ...patch } : stage));
    setDirty(true); setNotice("");
  }
  function move(index: number, direction: number) {
    const next = index + direction;
    if (next < 0 || next >= stages.length || stages[next]?.category !== "open") return;
    setStages(current => { const copy = [...current]; [copy[index], copy[next]] = [copy[next]!, copy[index]!]; return copy; });
    setDirty(true); setNotice("");
  }
  function discard() {
    const current = pipelines.find(pipeline => pipeline.id === selected) ?? pipelines[0];
    if (current) adopt(current); else startNew(); setNotice("");
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (saving || !canWrite) return;
    const stageNames = stages.map(stage => stage.name.trim());
    if (!name.trim() || stageNames.some(stageName => !stageName)) { setError("Give the pipeline and every stage a name."); return; }
    if (new Set(stageNames.map(stageName => stageName.toLocaleLowerCase())).size !== stageNames.length) { setError("Each stage needs a different name."); return; }
    if (creating && stageNames.some(stageName => ["won", "lost"].includes(stageName.toLowerCase()))) { setError("Won and Lost are added automatically. Choose different names for open stages."); return; }
    if (!stages.some(stage => stage.category === "open")) { setError("Keep at least one open stage in the pipeline."); return; }
    if (stages.some(stage => !Number.isInteger(stage.probability) || stage.probability < 0 || stage.probability > 100)) { setError("Stage probability must be a whole number from 0 to 100."); return; }
    setSaving(true); setError(""); setNotice("");
    try {
      const body = creating ? { name: name.trim(), stages: stageNames } : { name: name.trim(), stages: stages.map(stage => ({ ...(stage.id ? { id: stage.id } : {}), name: stage.name.trim(), probability: stage.probability, category: stage.category })) };
      requestKey.current = idempotencyRequest(body, requestKey.current);
      const result = await api<Pipeline>(creating ? "/pipelines" : `/pipelines/${selected}`, { method: creating ? "POST" : "PATCH", body: JSON.stringify(body), headers: { "Idempotency-Key": requestKey.current.key } });
      setPipelines(current => creating ? [...current, result] : current.map(pipeline => pipeline.id === result.id ? result : pipeline));
      adopt(result); requestKey.current = null;
      setNotice(creating ? "Pipeline created. Select it on the board to start adding deals." : "Pipeline saved. Existing deals keep their stage links.");
      onChanged?.();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Couldn't save this pipeline. Please retry."); }
    finally { setSaving(false); }
  }
  return <section className={styles.settings} aria-label="Pipeline settings">
    <header><h2>Shape your sales process</h2><p>Name the steps your team follows and set the probability of winning at each stage.</p></header>
    {loading ? <p role="status" className={styles.message}>Loading pipelines…</p> : <>
      <div className={styles.toolbar}><label>Pipeline<Select aria-label="Pipeline to configure" value={selected} disabled={saving || dirty || creating} onChange={event => { const pipeline = pipelines.find(item => item.id === event.target.value); if (pipeline) { adopt(pipeline); setNotice(""); } }}>
        {creating ? <option value="">New pipeline</option> : !pipelines.length ? <option value="">No pipelines yet</option> : pipelines.map(pipeline => <option key={pipeline.id} value={pipeline.id}>{pipeline.name}</option>)}
      </Select></label>{canWrite && <button type="button" className="button" disabled={saving || dirty || creating} onClick={startNew}><Icon name="plus" size={16} />New pipeline</button>}</div>
      {error && <div className={styles.error} role="alert">{error}{!pipelines.length && !creating && <button type="button" className="button" onClick={() => { setLoading(true); setError(""); setRevision(value => value + 1); }}>Retry</button>}</div>}
      {notice && <p className={styles.notice} role="status">{notice}</p>}
      {(selected || creating) && <form onSubmit={event => void save(event)}><fieldset disabled={saving || !canWrite} className={styles.fields}>
        <label className={styles.name}>Pipeline name<input required maxLength={100} value={name} placeholder="e.g. Enterprise sales" onChange={event => { setName(event.target.value); setDirty(true); setNotice(""); }} /></label>
        <div className={styles.stageHeading}><h3>Stages in order</h3><span>{creating ? "Won and Lost are added automatically." : "Won and Lost always keep their outcome."}</span></div>
        <div className={styles.stages}>{stages.map((stage, index) => <div className={styles.stage} key={stage.key}>
          <div className={styles.position}>{index + 1}</div>
          <label className={styles.stageName}>Stage name<input required maxLength={100} value={stage.name} onChange={event => change(index, { name: event.target.value })} aria-label={`Stage ${index + 1} name`} /></label>
          {!creating && <label className={styles.probability}>Win probability<div><input type="number" min={0} max={100} step={1} required value={Number.isNaN(stage.probability) ? "" : stage.probability} disabled={stage.category !== "open"} onChange={event => change(index, { probability: event.target.value === "" ? Number.NaN : Number(event.target.value) })} aria-label={`${stage.name || `Stage ${index + 1}`} probability`} /><span>%</span></div></label>}
          <div className={styles.stageActions}>{stage.category === "open" ? <>
            <button type="button" className="button" aria-label={`Move ${stage.name || "stage"} earlier`} disabled={index === 0 || stages[index - 1]?.category !== "open"} onClick={() => move(index, -1)}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="m6 14 6-6 6 6" /></svg></button>
            <button type="button" className="button" aria-label={`Move ${stage.name || "stage"} later`} disabled={index === stages.length - 1 || stages[index + 1]?.category !== "open"} onClick={() => move(index, 1)}><Icon name="down" size={16} /></button>
            <button type="button" className="button" aria-label={`Remove ${stage.name || "stage"}`} disabled={stages.filter(item => item.category === "open").length <= 1} onClick={() => { setStages(current => current.filter((_, position) => position !== index)); setDirty(true); setNotice(""); }}><Icon name="close" size={16} /></button>
          </> : <span className={styles.outcome}>{stage.category === "won" ? "Won outcome" : "Lost outcome"}</span>}</div>
        </div>)}</div>
        {canWrite && <button type="button" className="button" disabled={stages.filter(stage => stage.category === "open").length >= 12} onClick={() => { setStages(current => { const copy = [...current]; const index = copy.findIndex(stage => stage.category !== "open"); copy.splice(index === -1 ? copy.length : index, 0, { key: crypto.randomUUID(), name: "", probability: 50, category: "open" }); return copy; }); setDirty(true); setNotice(""); }}><Icon name="plus" size={16} />Add stage</button>}
        <p className={styles.help}>{creating ? "New open stages receive evenly spaced probabilities. You can adjust them after creating the pipeline." : "A stage used by a deal or its history cannot be removed. Saving a probability applies it to every open deal in that stage and updates the weighted forecast. Closed deals stay unchanged."}</p>
      </fieldset>{canWrite && <footer><span>{dirty ? "You have unsaved changes." : ""}</span><button type="button" className="button" disabled={saving || (!dirty && !creating)} onClick={discard}>Discard changes</button><button type="submit" className="button primary" disabled={saving || (!dirty && !creating)}>{saving ? "Saving…" : creating ? "Create pipeline" : "Save pipeline"}</button></footer>}</form>}
    </>}
  </section>;
}
