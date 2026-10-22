"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, amount } from "@/lib/api/client";
import type { ForecastReport } from "@/lib/api/schema";
import { Select } from "./ui/select";
import styles from "./forecast-panel.module.css";

type View = "open" | "won" | "lost" | "overdue" | "undated";
type Pipeline = { id: string; name: string };
function monthRange() {
  const day = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
  const [year, month] = day.split("-").map(Number);
  return { from: `${day.slice(0, 7)}-01`, to: `${day.slice(0, 7)}-${new Date(year!, month!, 0).getDate()}` };
}
const views: { id: View; label: string }[] = [
  { id: "open", label: "Expected to close" }, { id: "won", label: "Won" },
  { id: "lost", label: "Lost" }, { id: "overdue", label: "Overdue closes" },
  { id: "undated", label: "Missing close date" },
];

export function ForecastPanel() {
  const [dates, setDates] = useState(monthRange);
  const [pipeline, setPipeline] = useState("");
  const [owner, setOwner] = useState("");
  const [team, setTeam] = useState<{ id: string; name: string; is_active: boolean }[]>([]);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [view, setView] = useState<View>("open");
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<{ key: string; data?: ForecastReport; error?: string }>({ key: "" });
  const [pipelineError, setPipelineError] = useState("");
  const params = new URLSearchParams({ date_from: dates.from, date_to: dates.to, view, limit: "20", offset: String(offset) });
  if (pipeline) params.set("pipeline_id", pipeline);
  if (owner) params.set("owner_id", owner);
  const key = params.toString();
  const loading = state.key !== key || (!state.data && !state.error);
  const report = state.key === key ? state.data : undefined;
  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([api<{ items: Pipeline[] }>("/pipelines", { signal: controller.signal }), api<{ id: string; name: string; is_active: boolean }[]>("/team", { signal: controller.signal })])
      .then(([result, members]) => { if (!controller.signal.aborted) { setPipelines(result.items); setTeam(members); setPipelineError(""); } })
      .catch(error => { if (!controller.signal.aborted) setPipelineError((error as Error).message); });
    return () => controller.abort();
  }, [revision]);
  useEffect(() => {
    const controller = new AbortController();
    void api<ForecastReport>(`/reports/sales?${key}`, { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setState({ key, data }); })
      .catch(error => { if (!controller.signal.aborted) setState({ key, error: (error as Error).message }); });
    return () => controller.abort();
  }, [key, revision]);
  function retry() { setState({ key: "" }); setRevision(value => value + 1); }
  function changeView(next: View) { setView(next); setOffset(0); }
  return <section className={styles.report} aria-label="Sales forecast">
    <header className={styles.intro}><div><h2>Know what is likely to close.</h2><p>Expected closes, actual outcomes and the deals that need attention.</p></div><Link href="/deals" className="button">Open pipeline</Link></header>
    <div className={styles.filters}>
      <label>From<input type="date" aria-label="Forecast from" required value={dates.from} onChange={event => { setDates({ ...dates, from: event.target.value }); setOffset(0); }}/></label>
      <label>To<input type="date" aria-label="Forecast to" required value={dates.to} onChange={event => { setDates({ ...dates, to: event.target.value }); setOffset(0); }}/></label>
      <label className={styles.pipeline}>Pipeline<Select aria-label="Forecast pipeline" value={pipeline} onChange={event => { setPipeline(event.target.value); setOffset(0); }}><option value="">All pipelines</option>{pipelines.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></label>
      <label className={styles.pipeline}>Owner<Select aria-label="Forecast owner" value={owner} onChange={event => { setOwner(event.target.value); setOffset(0); }}><option value="">All accessible owners</option>{team.map(member => <option key={member.id} value={member.id}>{member.name}{member.is_active ? "" : " (inactive)"}</option>)}</Select></label>
      <button className="button" onClick={() => { setDates(monthRange()); setOffset(0); }}>This month</button>
    </div>
    <p className={styles.basis}>Open deals use expected close dates. Won and lost deals use actual closing dates in IST. Weighted value is an estimate, not booked revenue.</p>
    {pipelineError && <p role="alert">Pipeline filters could not load: {pipelineError} <button className="button" onClick={retry}>Retry</button></p>}
    {state.key === key && state.error && <div className={styles.error} role="alert"><p>{state.error}</p><button className="button" onClick={retry}>Retry report</button></div>}
    {loading && <p className={styles.message} role="status">Calculating your forecast…</p>}
    {report && <>
      <dl className={styles.summary}>
        <div><dt>Expected pipeline</dt><dd>{amount(report.summary.open_value)}</dd><small>{report.summary.open_count} open deals in this period</small></div>
        <div><dt>Weighted forecast</dt><dd>{amount(report.summary.weighted_value)}</dd><small>Value × win probability</small></div>
        <div><dt>Won deal value</dt><dd>{amount(report.summary.won_value)}</dd><small>{report.summary.won_count} deals closed won</small></div>
        <div><dt>Win rate</dt><dd>{report.summary.win_rate}%</dd><small>{report.summary.won_count} won · {report.summary.lost_count} lost</small></div>
      </dl>
      <div className={styles.attention}><span>Keep the forecast useful</span><button onClick={() => changeView("overdue")}>{report.summary.overdue_count} overdue close dates</button><button onClick={() => changeView("undated")}>{report.summary.undated_count} missing close dates</button></div>
      {report.months.length > 1 && <div className={styles.tableWrap}><table><caption>Monthly outlook</caption><thead><tr><th scope="col">Month</th><th scope="col">Open pipeline</th><th scope="col">Weighted</th><th scope="col">Won</th><th scope="col">Lost</th></tr></thead><tbody>{report.months.map(month => <tr key={month.month}><th scope="row">{month.month}</th><td>{amount(month.open_value)}</td><td>{amount(month.weighted_value)}</td><td>{amount(month.won_value)}</td><td>{amount(month.lost_value)}</td></tr>)}</tbody></table></div>}
      <section className={styles.detail} aria-label="Forecast deals"><div className={styles.detailHeader}><h3>Behind the numbers</h3><span>{report.total} matching deals</span></div>
        <div className={styles.views} role="group" aria-label="Forecast deal view">{views.map(item => <button key={item.id} aria-pressed={view === item.id} onClick={() => changeView(item.id)}>{item.label}</button>)}</div>
        {(view === "overdue" || view === "undated") && <p className={styles.basis}>Attention lists cover all open deals in the selected pipeline, regardless of the date range above.</p>}
        {report.items.length ? <div className={styles.tableWrap}><table><thead><tr><th scope="col">Opportunity</th><th scope="col">Stage</th><th scope="col">Value</th><th scope="col">Probability</th><th scope="col">{view === "won" || view === "lost" ? "Closed on" : "Expected close"}</th>{view === "lost" && <th scope="col">Loss reason</th>}</tr></thead><tbody>{report.items.map(deal => <tr key={deal.id}><th scope="row"><Link href={`/deals?id=${deal.id}`}>{deal.name}</Link></th><td>{deal.stage}</td><td>{amount(deal.amount)}</td><td>{deal.probability}%</td><td>{deal.close_date || "Not set"}</td>{view === "lost" && <td>{deal.lost_reason}</td>}</tr>)}</tbody></table></div> : <div className={styles.message}><p>{view === "open" ? "No deals are expected to close in this period." : "No deals match this view."}</p><Link href="/deals">Review your pipeline</Link></div>}
        <footer className={styles.pagination}><span>{report.total ? `${offset + 1}–${Math.min(offset + 20, report.total)} of ${report.total}` : "0 deals"}</span><button className="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous</button><button className="button" disabled={offset + 20 >= report.total} onClick={() => setOffset(offset + 20)}>Next</button></footer>
      </section>
    </>}
  </section>;
}
