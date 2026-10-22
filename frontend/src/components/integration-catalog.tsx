"use client";

import { useState } from "react";
import Link from "next/link";
import { text, type Row } from "@/lib/api/client";
import styles from "./lead-capture.module.css";

const planned = [
  {name:"Gmail & Outlook", description:"Email sync, replies and shared customer conversations.", available:"Write and save customer-linked email drafts now.", href:"/communications", action:"Open email workspace"},
  {name:"Google & Microsoft Calendar", description:"Two-way calendar sync for meetings and follow-ups.", available:"Schedule tasks and meetings in the local CRM calendar.", href:"/calendar", action:"Open CRM calendar"},
  {name:"WhatsApp Business", description:"Customer messaging through an approved business account.", available:"Keep customer phone details and log calls or follow-up tasks.", href:"/activities", action:"Open tasks & activities"},
  {name:"Slack & Microsoft Teams", description:"Team notifications in your external workspace.", available:"Automation notifications are available inside Relay.", href:"/automations", action:"Open automations"},
];

export function IntegrationCatalog({integrations}:{integrations:Row[]}) {
  const [expanded,setExpanded]=useState<string|null>(null);
  return <div className={styles.workspace}><div><h2>Connected tools</h2><p className="muted">Your CRM workflows run locally. External provider connections are planned for a later release.</p></div>{integrations.length>0&&<div className="integration-list">{integrations.map((row,index)=><div key={row.id??index}><div><strong>{text(row.name??row.provider)}</strong><p>{text(row.description??row.message)}</p></div><span>{text(row.status).replaceAll("_", " ")||"Not connected"}</span></div>)}</div>}<div className={styles.cards}>{planned.map(item=><article className={styles.card} key={item.name}><div className={styles.header}><h3>{item.name}</h3><span className={styles.status}>Planned · Not connected</span></div><p className="muted">{item.description}</p><button className="button secondary" aria-expanded={expanded===item.name} onClick={()=>setExpanded(expanded===item.name?null:item.name)}>View connection details</button>{expanded===item.name&&<div className={styles.receipt}><p>This connector is not implemented in the local hackathon build. No account is connected and no data is sent to this provider.</p><p>{item.available}</p><Link className="button subtle" href={item.href}>{item.action} →</Link></div>}</article>)}</div></div>;
}
