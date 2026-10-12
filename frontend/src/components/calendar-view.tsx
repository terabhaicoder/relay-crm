"use client";

import { useEffect, useState } from "react";
import { api, Row, text } from "@/lib/api/client";
import styles from "./calendar-view.module.css";

type CalendarDay = { date: string; count: number; items: Row[] };
type CalendarData = { days: CalendarDay[]; total: number };
const dateKey = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
const todayKey = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());

export function CalendarView({ query, status, revision, canWrite, onSelect, onCreate }: {
  query: string; status: string; revision: number; canWrite: boolean;
  onSelect: (record: Row) => void; onCreate: (date: string) => void;
}) {
  const [month, setMonth] = useState(() => todayKey().slice(0, 7));
  const [selected, setSelected] = useState(todayKey);
  const [page, setPage] = useState(0);
  const [retry, setRetry] = useState(0);
  const [previousFilter, setPreviousFilter] = useState(`${query}/${status}`);
  if (previousFilter !== `${query}/${status}`) { setPreviousFilter(`${query}/${status}`); setPage(0); }
  const [summary, setSummary] = useState<{ scope: string; data?: CalendarData; error?: string }>({ scope: "" });
  const [agenda, setAgenda] = useState<{ scope: string; items?: Row[]; total?: number; error?: string }>({ scope: "" });
  const first = new Date(`${month}-01T12:00:00`);
  const start = new Date(first);
  start.setDate(start.getDate() - (start.getDay() + 6) % 7);
  const days = Array.from({ length: 42 }, (_, index) => { const date = new Date(start); date.setDate(date.getDate() + index); return date; });
  const from = dateKey(start), to = dateKey(days[41]!);
  const scope = JSON.stringify([from, to, query, status, revision, retry]);
  const agendaScope = JSON.stringify([selected, query, status, page, revision, retry]);
  useEffect(() => {
    let active = true;
    const params = new URLSearchParams({ from_date: from, to_date: to, q: query, status });
    api<CalendarData>(`/calendar?${params}`).then(data => { if (active) setSummary({ scope, data }); })
      .catch((error: Error) => { if (active) setSummary({ scope, error: error.message }); });
    return () => { active = false; };
  }, [from, to, query, status, scope]);
  useEffect(() => {
    let active = true;
    const params = new URLSearchParams({ date_from: selected, date_to: selected, q: query, limit: "20", offset: String(page * 20), sort: "due_date", order: "asc" });
    if (status) params.set("status", status);
    api<{ items: Row[]; total: number }>(`/activities?${params}`).then(data => { if (active) setAgenda({ scope: agendaScope, ...data }); })
      .catch((error: Error) => { if (active) setAgenda({ scope: agendaScope, error: error.message }); });
    return () => { active = false; };
  }, [selected, query, status, page, agendaScope]);
  function move(delta: number) {
    const next = new Date(first); next.setMonth(next.getMonth() + delta);
    setMonth(dateKey(next).slice(0, 7)); setSelected(dateKey(next)); setPage(0);
  }
  const ready = summary.scope === scope;
  const agendaReady = agenda.scope === agendaScope;
  const label = first.toLocaleDateString("en-IN", { month: "long", year: "numeric" });
  const error = ready ? summary.error : undefined;
  return <div className={styles.layout}>
    <section className={styles.calendar} aria-label="Activity calendar">
      <header className={styles.header}><div><h2>{label}</h2><p>{ready && summary.data ? `${summary.data.total} activities across the displayed dates` : "Loading activities…"} · IST</p></div><div className={styles.actions}>
        <button type="button" className="button subtle" aria-label="Previous month" onClick={() => move(-1)}>Previous</button>
        <button type="button" className="button subtle" onClick={() => { setMonth(todayKey().slice(0, 7)); setSelected(todayKey()); setPage(0); }}>Today</button>
        <button type="button" className="button subtle" aria-label="Next month" onClick={() => move(1)}>Next</button>
      </div></header>
      {error ? <div role="alert" className={styles.notice}>{error} <button className="button subtle" onClick={() => setRetry(retry + 1)}>Try again</button></div> : <>
        <div className={styles.weekdays}>{["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map(day => <span key={day}>{day}</span>)}</div>
        <div className={styles.grid} aria-busy={!ready}>{days.map(date => {
          const key = dateKey(date), data = ready ? summary.data?.days.find(day => day.date === key) : undefined;
          return <button type="button" key={key} className={`${styles.day} ${key.slice(0, 7) !== month ? styles.outside : ""} ${selected === key ? styles.selected : ""}`} aria-pressed={selected === key} aria-label={`${key}, ${data?.count ?? 0} activities`} onClick={() => { setSelected(key); setPage(0); }}>
            <span className={key === todayKey() ? styles.today : styles.number}>{date.getDate()}</span>
            <span className={styles.previews}>{data?.items.map(row => <span key={row.id} className={row.status === "completed" ? styles.completed : ""}>{text(row.name)}</span>)}</span>
            {!!data?.count && <small>{data.count} {data.count === 1 ? "activity" : "activities"}</small>}
          </button>;
        })}</div>
      </>}
    </section>
    <section className={styles.agenda} aria-label="Selected day activities"><header className={styles.header}><div><h2>{new Date(`${selected}T12:00:00`).toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}</h2><p>All activities for this day</p></div>{canWrite && <button type="button" className="button primary" onClick={() => onCreate(selected)}>Add activity</button>}</header>
      {!agendaReady ? <p role="status" className={styles.notice}>Loading this day…</p> : agenda.error ? <p role="alert" className={styles.notice}>{agenda.error} <button className="button subtle" onClick={() => setRetry(retry + 1)}>Try again</button></p> : !agenda.items?.length ? <p className={styles.notice}>No activities match this day. Select another date or add your next follow-up.</p> : <div className={styles.rows}>{agenda.items.map(row => <button type="button" key={row.id} onClick={() => onSelect(row)}><span><strong>{text(row.name)}</strong><small>{text(row.type)} · {text(row.priority)} priority</small></span><span>{row.status === "completed" ? "Completed" : "Pending"}</span></button>)}</div>}
      {agendaReady && !!agenda.total && <footer className={styles.pagination}><span>{page * 20 + 1}–{Math.min((page + 1) * 20, agenda.total)} of {agenda.total}</span><button className="button subtle" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous activities</button><button className="button subtle" disabled={(page + 1) * 20 >= agenda.total} onClick={() => setPage(page + 1)}>Next activities</button></footer>}
    </section>
  </div>;
}
