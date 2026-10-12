"use client";

import Link from "next/link";
import { useState } from "react";
import { Icon } from "@/components/icon";
import styles from "./landing.module.css";

const journey = [
  { title: "Meet your next customer.", name: "Lead", icon: "leads", description: "Capture the first conversation, assign an owner, and make the next follow-up clear.", detail: "A name becomes a relationship.", fields: ["Contact details", "Lead source", "Next follow-up"], action: "Qualify & convert", next: "Connected contact + company + deal" },
  { title: "Give every deal a next step.", name: "Deal", icon: "deals", description: "Keep your pipeline moving with stages, activities, and a shared record of what happens next.", detail: "The whole conversation travels with you.", fields: ["Company & contact", "Deal stage", "Activities & history"], action: "Record the outcome", next: "A customer relationship, ready for the next team" },
  { title: "Make the handoff feel seamless.", name: "Support", icon: "tickets", description: "Connect support tickets to the customer and deal, with internal notes that keep your team aligned.", detail: "A new team. The same customer story.", fields: ["Customer context", "Priority & owner", "Internal conversation"], action: "Resolve & follow through", next: "A customer story your team can return to" },
] as const;
const questions = [
  ["Who is Relay built for?", "B2B sales and customer support teams that want leads, companies, contacts, deals, tasks and tickets in one shared workspace."],
  ["Can I bring my existing customer data?", "Yes. Import CSV files with row-level validation and duplicate handling. You can download an error report, correct invalid rows and export the records you have permission to access."],
  ["Can sales and support work from the same customer record?", "Yes. Lead conversion connects the contact, company and deal. Support tickets and activities can link to those records so the next team keeps the customer context."],
  ["Does Relay send email or connect to Gmail?", "Email templates and drafts are available. Gmail connection and sending are not enabled in this release; saved drafts and support replies are clearly marked as unsent."],
  ["Can I control who sees customer information?", "Workspace roles govern access on the server. Sales representatives see their own records, read-only teammates cannot make changes, and each workspace is isolated from other organizations."],
];

export function Landing() {
  const [step, setStep] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const current = journey[step] ?? journey[0];
  return (
    <div className={styles.page}>
      <a href="#landing-content" className={styles.skip}>Skip to content</a>
      <header className={styles.header}>
        <Link href="/" aria-label="Relay home" className={styles.logo}><span className={styles.mark}>r</span>relay<span className={styles.logoDot}>.</span></Link>
        <nav aria-label="Website navigation" className={styles.desktopNav}>
          <a href="#workflow">How it works</a><a href="#features">Your workspace</a><a href="#questions">Questions</a>
        </nav>
        <div className={styles.headerActions}><Link href="/dashboard" className={styles.signIn}>Sign in</Link><Link className={styles.smallCta} href="/dashboard?signup=1">Get started <Icon name="arrow" size={17}/></Link><button type="button" className={styles.menuButton} aria-label={menuOpen ? "Close navigation" : "Open navigation"} aria-expanded={menuOpen} aria-controls="landing-navigation" onClick={() => setMenuOpen(!menuOpen)}><Icon name={menuOpen ? "close" : "menu"}/></button></div>
      </header>
      {menuOpen && <nav id="landing-navigation" aria-label="Mobile website navigation" className={styles.mobileNav}><a href="#workflow" onClick={() => setMenuOpen(false)}>How it works</a><a href="#features" onClick={() => setMenuOpen(false)}>Your workspace</a><a href="#questions" onClick={() => setMenuOpen(false)}>Questions</a><Link href="/dashboard">Sign in to Relay</Link></nav>}
      <main id="landing-content">
        <section className={styles.hero}>
          <div className={styles.heroCopy}>
            <h1>Good relationships<br/>deserve a <em>great relay.</em></h1>
            <p>From the first hello to the next happy customer. Bring your B2B sales and support teams together, with every conversation in context.</p>
            <div className={styles.heroActions}><Link href="/dashboard?signup=1" className={styles.primary}>Bring your team together <Icon name="arrow" size={20}/></Link><a href="#workflow" className={styles.textLink}>See how it connects <Icon name="down" size={16}/></a></div>
            <div className={styles.heroFootnote}><span className={styles.people} aria-hidden="true"><Icon name="contacts" size={20}/></span><span>One workspace for the people behind your pipeline.</span></div>
          </div>
          <div className={styles.journeyPreview} aria-label="Illustration of Relay's connected customer journey">
            <div className={styles.previewHeader}><span className={styles.previewDot}/><span>A connected customer journey</span><Icon name="arrow" size={18}/></div>
            <div className={styles.previewStage}><div className={styles.stageIcon}><Icon name="leads" size={23}/></div><div><h2>A promising conversation</h2><p>Capture the lead. Remember the next step.</p></div><span className={styles.status}>New lead</span></div>
            <div className={styles.connector}><span/><p>Qualify & convert</p><Icon name="down" size={14}/></div>
            <div className={styles.linkedRow}><span><Icon name="contacts" size={18}/> Contact</span><span><Icon name="accounts" size={18}/> Company</span><span><Icon name="deals" size={18}/> Deal</span></div>
            <div className={styles.connector}><span/><p>Keep the context</p><Icon name="down" size={14}/></div>
            <div className={styles.supportStage}><div className={styles.stageIcon}><Icon name="tickets" size={23}/></div><div><h2>A thoughtful handoff</h2><p>Sales context, ready for customer support.</p></div><Icon name="check" size={20}/></div>
            <div className={styles.previewFooter}><Icon name="clock" size={15}/><span>People, activity and history stay connected.</span></div>
          </div>
        </section>
        <div className={styles.moduleStrip} aria-label="Connected CRM modules"><span>Leads & contacts</span><Icon name="plus" size={14}/><span>Companies & deals</span><Icon name="plus" size={14}/><span>Tasks & follow-ups</span><Icon name="plus" size={14}/><span>Customer support</span></div>
        <section id="workflow" className={styles.workflow}>
          <div className={styles.sectionIntro}><h2>More momentum.<br/><em>Fewer loose ends.</em></h2><p>Keep the relationship moving without making your team piece the story back together.</p></div>
          <div className={styles.workflowGrid}>
            <div className={styles.steps} role="tablist" aria-orientation="vertical" aria-label="Customer journey stages">
              {journey.map((entry, index) => <button key={entry.name} id={`journey-tab-${index}`} role="tab" aria-selected={step === index} aria-controls="journey-panel" tabIndex={step === index ? 0 : -1} className={step === index ? styles.activeStep : styles.step} onClick={() => setStep(index)} onKeyDown={event => { const next = event.key === "ArrowDown" || event.key === "ArrowRight" ? (step + 1) % journey.length : event.key === "ArrowUp" || event.key === "ArrowLeft" ? (step + journey.length - 1) % journey.length : event.key === "Home" ? 0 : event.key === "End" ? journey.length - 1 : null; if (next !== null) { event.preventDefault(); setStep(next); document.getElementById(`journey-tab-${next}`)?.focus(); } }}><span className={styles.stepTop}><Icon name={entry.icon} size={20}/><strong>{entry.title}</strong><Icon name="arrow" size={18}/></span><span className={styles.stepDescription}>{entry.description}</span></button>)}
            </div>
            <div id="journey-panel" role="tabpanel" tabIndex={0} aria-labelledby={`journey-tab-${step}`} className={styles.storyPanel}>
              <div className={styles.storyTop}><span className={styles.storyLogo}>r</span><span>Customer journey / {current.name}</span></div><h3>{current.detail}</h3>
              <dl className={styles.fields}>{current.fields.map((field, index) => <div key={field}><dt>{field}</dt><dd><span className={styles.fieldLine} style={{width:`${76-index*13}%`}}/><Icon name="check" size={16}/></dd></div>)}</dl>
              <div className={styles.storyAction}><span>{current.action}</span><Icon name="arrow" size={19}/></div><p className={styles.storyOutcome}><Icon name="check" size={17}/>{current.next}</p><small>Workflow illustration. Your workspace starts with your own data.</small>
            </div>
          </div>
        </section>
        <section id="features" className={styles.features}>
          <div className={styles.featureHeading}><h2>The whole picture.<br/>A calmer working day.</h2><p>Practical tools for the everyday work of building customer relationships.</p></div>
          <div className={styles.featureRows}>
            <article><Icon name="search" size={25}/><div><h3>Find the context. Pick up the conversation.</h3><p>Search across records, follow linked contacts and companies, and see activities and history where you need them.</p></div><span>Customer context</span></article>
            <article><Icon name="activities" size={25}/><div><h3>Turn your next step into a habit.</h3><p>Use tasks, calendar views and conditional automations to turn customer events into follow-up work and notifications.</p></div><span>Team follow-through</span></article>
            <article><Icon name="reports" size={25}/><div><h3>Work from what is actually happening.</h3><p>See your open pipeline and customer activity from live records. Filter your views and bring data in or out with CSV.</p></div><span>Shared visibility</span></article>
          </div>
        </section>
        <section className={styles.teamSection}><div className={styles.teamCopy}><h2>A good handoff<br/>changes everything.</h2><p>Sales knows how the relationship began. Support knows what the customer needs next. Relay gives both teams somewhere to meet.</p><Link href="/dashboard" className={styles.lightCta}>Explore your workspace <Icon name="arrow" size={19}/></Link></div><div className={styles.handoff}><div className={styles.handoffPerson}><Icon name="deals" size={32}/><h3>Sales</h3><p>The conversation.<br/>The company.<br/>The opportunity.</p></div><div className={styles.handoffLine}><span/><div className={styles.handoffMark}>r</div><span/></div><div className={styles.handoffPerson}><Icon name="tickets" size={32}/><h3>Support</h3><p>The context.<br/>The next question.<br/>The relationship.</p></div></div></section>
        <section id="questions" className={styles.faq}><div><h2>A few things<br/>you might be wondering.</h2><p>Clear answers before your first hello.</p></div><div className={styles.questions}>{questions.map(([question,answer]) => <details key={question}><summary>{question}<Icon name="plus" size={18}/></summary><p>{answer}</p></details>)}</div></section>
        <section className={styles.close}><span className={styles.closeMark}>r</span><h2>Your next chapter<br/>starts with a conversation.</h2><p>Give your team a shared place to carry it forward.</p><Link href="/dashboard?signup=1" className={styles.primary}>Get started with Relay <Icon name="arrow" size={20}/></Link></section>
      </main>
      <footer className={styles.footer}><Link href="/" className={styles.footerLogo}>relay.</Link><p>Built for better relationships.</p><div><a href="#workflow">How it works</a><a href="#questions">Questions</a><Link href="/dashboard">Open workspace <Icon name="arrow" size={15}/></Link></div></footer>
    </div>
  );
}
