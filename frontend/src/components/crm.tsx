"use client";

import { Select } from "@/components/ui/select";
import { CustomerContext } from "./customer-context";
import { CampaignMembers } from "./campaign-members";
import { SalesWorkbench } from "./sales-workbench";
import { PipelineSettings } from "./pipeline-settings";
import { CalendarView } from "./calendar-view";
import { PipelineBoard } from "./pipeline-board";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  FormEvent,
  RefObject,
  ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { api, ApiError, amount, formatTimestamp, idempotencyRequest, Row, submittedDate, text, User } from "@/lib/api/client";
import { Icon } from "./icon";
import { ActiveSessions, TeamInvitations } from "./account-access";
import { AutomationConditions } from "./automation-conditions";
import type { Condition } from "@/lib/api/schema";

type List = { items: Row[]; total: number };
type Stage = {
  id: string;
  name: string;
  probability: number;
  color: string;
  category: string;
};
type Pipeline = { id: string; name: string; stages: Stage[] };
type Field = {
  key: string;
  label: string;
  type?: string;
  options?: string[];
  required?: boolean;
  wide?: boolean;
};
const navigation: [string, string][] = [
  ["dashboard", "Overview"],
  ["workbench", "My Day"],
  ["leads", "Leads"],
  ["contacts", "Contacts"],
  ["accounts", "Companies"],
  ["deals", "Pipeline"],
  ["activities", "My tasks"],
  ["calendar", "Calendar"],
  ["campaigns", "Campaigns"],
  ["tickets", "Support"],
  ["reports", "Reports"],
  ["automations", "Automations"],
  ["communications", "Email workspace"],
  ["settings", "Settings"],
];
const entityFor = (section: string) =>
  ({
    accounts: "parties",
    calendar: "activities",
    communications: "email/messages",
  })[section] ?? section;
const sortDateField = (section: string) =>
  ["automations", "communications"].includes(section) ? "created_at" : "updated_at";
const singular: Record<string, string> = {
  leads: "lead",
  contacts: "contact",
  accounts: "company",
  deals: "deal",
  activities: "task",
  calendar: "activity",
  campaigns: "campaign",
  tickets: "ticket",
  automations: "automation",
  communications: "email",
};
const descriptions: Record<string, string> = {
  workbench: "Follow-ups, opportunities and support that need your attention.",
  pipelines: "Make the sales process work for your team.",
  leads: "Good conversations start with the right people.",
  contacts: "The people behind your customer relationships.",
  accounts: "Keep every customer relationship in context.",
  deals: "A clear view of what is moving, and what needs a nudge.",
  activities: "Make room for the next important conversation.",
  calendar: "Your upcoming meetings, calls, and follow-ups.",
  campaigns: "Turn your outreach into lasting relationships.",
  tickets: "A little attention makes a big difference.",
  reports: "The story behind your sales activity.",
  automations: "Let routine work take care of itself.",
  communications: "Prepare email templates and drafts. Sending is not enabled.",
  settings: "Make this workspace work for your team.",
};
const fields: Record<string, Field[]> = {
  leads: [
    { key: "name", label: "Full name", required: true },
    { key: "company", label: "Company" },
    { key: "email", label: "Email", type: "email" },
    { key: "phone", label: "Phone", type: "tel" },
    { key: "title", label: "Job title" },
    {
      key: "source",
      label: "Source",
      options: [
        "Website",
        "Referral",
        "LinkedIn",
        "Event",
        "Cold outreach",
        "Other",
      ],
    },
    {
      key: "status",
      label: "Status",
      options: ["New", "Contacted", "Qualified", "Unqualified"],
    },
    { key: "value", label: "Estimated value (₹)", type: "number" },
    { key: "next_follow_up", label: "Next follow-up", type: "date" },
    { key: "notes", label: "Notes", type: "textarea", wide: true },
  ],
  contacts: [
    { key: "name", label: "Full name", required: true },
    { key: "party_id", label: "Linked company", type: "relation:parties" },
    { key: "company", label: "Company" },
    { key: "email", label: "Email", type: "email" },
    { key: "phone", label: "Phone", type: "tel" },
    { key: "title", label: "Job title" },
    { key: "notes", label: "Notes", type: "textarea", wide: true },
  ],
  accounts: [
    { key: "name", label: "Company name", required: true },
    { key: "industry", label: "Industry" },
    { key: "email", label: "Email", type: "email" },
    { key: "phone", label: "Phone", type: "tel" },
    { key: "website", label: "Website", type: "url" },
    { key: "city", label: "City" },
    { key: "notes", label: "Notes", type: "textarea", wide: true },
  ],
  deals: [
    { key: "name", label: "Deal name", required: true },
    { key: "party_id", label: "Company", type: "relation:parties" },
    { key: "contact_id", label: "Contact", type: "relation:contacts" },
    { key: "amount", label: "Deal value (₹)", type: "number", required: true },
    { key: "stage_id", label: "Stage", type: "stage" },
    { key: "expected_close_date", label: "Expected close", type: "date" },
    { key: "notes", label: "Notes", type: "textarea", wide: true },
  ],
  activities: [
    { key: "name", label: "What needs to happen?", required: true, wide: true },
    {
      key: "entity_type",
      label: "Related record type",
      options: ["", "leads", "contacts", "parties", "deals", "tickets"],
    },
    { key: "entity_id", label: "Related record", type: "relation:dynamic" },
    {
      key: "type",
      label: "Activity type",
      options: ["task", "call", "meeting", "follow-up", "email", "note"],
    },
    { key: "priority", label: "Priority", options: ["medium", "high", "low"] },
    { key: "due_date", label: "Due date", type: "date" },
    { key: "status", label: "Status", options: ["pending", "completed"] },
    { key: "notes", label: "Notes", type: "textarea", wide: true },
  ],
  campaigns: [
    { key: "name", label: "Campaign name", required: true },
    {
      key: "type",
      label: "Channel",
      options: ["email", "event", "social", "referral", "other"],
    },
    {
      key: "status",
      label: "Status",
      options: ["draft", "active", "completed"],
    },
    { key: "budget", label: "Budget (₹)", type: "number" },
    { key: "spent", label: "Actual spend (₹)", type: "number" },
    { key: "start_date", label: "Start date", type: "date" },
    { key: "end_date", label: "End date", type: "date" },
    { key: "notes", label: "Notes", type: "textarea", wide: true },
  ],
  tickets: [
    { key: "name", label: "Subject", required: true, wide: true },
    { key: "party_id", label: "Company", type: "relation:parties" },
    { key: "contact_id", label: "Contact", type: "relation:contacts" },
    { key: "deal_id", label: "Related deal", type: "relation:deals" },
    {
      key: "priority",
      label: "Priority",
      options: ["medium", "low", "high", "urgent"],
    },
    {
      key: "status",
      label: "Status",
      options: ["New", "Open", "Pending", "Resolved", "Closed"],
    },
    { key: "category", label: "Category" },
    { key: "description", label: "Description", type: "textarea", wide: true },
  ],
  automations: [
    { key: "name", label: "Automation name", required: true },
    {
      key: "action_text",
      label: "Task or notification text",
      required: true,
      wide: true,
    },
    { key: "due_days", label: "Task due in days", type: "number" },
    {
      key: "trigger",
      label: "Trigger",
      options: ["leads.created", "deals.won", "tickets.created"],
    },
    { key: "action", label: "Action", options: ["create_task", "notify"] },
  ],
  communications: [
    {
      key: "recipient",
      label: "To",
      type: "email",
      required: true,
      wide: true,
    },
    { key: "subject", label: "Subject", required: true, wide: true },
    {
      key: "body",
      label: "Message",
      type: "textarea",
      wide: true,
      required: true,
    },
  ],
};
const columns: Record<string, string[]> = {
  leads: ["name", "company", "status", "source", "value", "next_follow_up"],
  contacts: ["name", "company", "email", "phone", "title"],
  accounts: ["name", "industry", "city", "email", "phone"],
  deals: ["name", "amount", "stage_id", "status", "expected_close_date"],
  activities: ["name", "type", "priority", "due_date", "status"],
  campaigns: ["name", "type", "status", "budget", "spent", "start_date"],
  tickets: ["name", "priority", "status", "category", "created_at"],
  automations: ["name", "trigger", "action", "enabled"],
  communications: ["subject", "recipient", "status", "created_at"],
};
const label = (key: string) =>
  ({
    name: "Name",
    stage_id: "Stage",
    value: "Est. value",
    next_follow_up: "Follow-up",
    expected_close_date: "Expected close",
    due_date: "Due",
    created_at: "Created",
    recipient: "Recipient",
  })[key] ?? key.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
const initials = (name: string) =>
  name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
function Badge({ value }: { value: unknown }) {
  const content = text(value);
  return (
    <span
      className={`badge badge-${content.toLowerCase().replaceAll(" ", "-")}`}
    >
      {content || "—"}
    </span>
  );
}
function Empty({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action?: () => void;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Icon name="leads" size={28} />
      </div>
      <h3>{title}</h3>
      <p>{detail}</p>
      {action && (
        <button className="button primary" onClick={action}>
          <Icon name="plus" size={16} />
          Create the first one
        </button>
      )}
    </div>
  );
}

/** The root layout keeps authentication and the shell mounted between modules. */
export function WorkspaceRouter({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const section = pathname.split("/")[1] ?? "";
  if (pathname === `/${section}` && (navigation.some(([key]) => key === section) || section === "pipelines")) {
    return <CRM section={section} />;
  }
  return children;
}

function SectionLoading({ title }: { title: string }) {
  return (
    <div className="loading-block" role="status" aria-label={`Loading ${title}`} data-testid="section-loading" style={{ minHeight: 280 }}>
      <div style={{ width: "100%", display: "grid", gap: 20 }} aria-hidden="true">
        {[86, 72, 94, 64].map((width, index) => <div key={index} style={{ height: 15, width: `${width}%`, borderRadius: 4, background: "var(--border, #e0e5df)" }} />)}
      </div>
      <span>Loading your {title.toLowerCase()}…</span>
    </div>
  );
}

export function CRM({ section }: { section: string }) {
  const router = useRouter();
  const routeSearch = useSearchParams();
  const activeRecordId = routeSearch.get("id");
  const routeQuery = routeSearch.get("q");
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState(routeQuery ?? "");
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState(`${sortDateField(section)}:desc`);
  const [loading, setLoading] = useState(false);
  const [loadedScope, setLoadedScope] = useState("");
  const [failedScope, setFailedScope] = useState("");
  const [previousRoute, setPreviousRoute] = useState({ section, routeQuery });
  const [previousRecordId, setPreviousRecordId] = useState(activeRecordId);
  const [recordLoading, setRecordLoading] = useState(Boolean(activeRecordId && singular[section]));
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState("");
  const [workspaceRevision, setWorkspaceRevision] = useState(0);
  const [editor, setEditor] = useState<Row | "new" | null>(null);
  const [view, setView] = useState("board");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [dashboard, setDashboard] = useState<Record<string, unknown>>({});
  const [tasks, setTasks] = useState<Row[]>([]);
  const [recentDeals, setRecentDeals] = useState<Row[]>([]);
  const normalized = section === "calendar" ? "activities" : section;
  const canWrite =
    Boolean(user) &&
    !["Read-only", "Read-only/CA", "Viewer"].includes(user?.role ?? "") &&
    (section !== "automations" ||
      ["Owner", "Admin", "Sales Manager"].includes(user?.role ?? ""));
  const requestSequence = useRef(0);
  const clearWorkspace = useCallback(() => {
    requestSequence.current += 1;
    setRows([]);
    setTotal(0);
    setPage(0);
    setQuery("");
    setFilter("");
    setSort(`${sortDateField(section)}:desc`);
    setDashboard({});
    setTasks([]);
    setRecentDeals([]);
    setPipelines([]);
    setEditor(null);
    setSearchOpen(false);
    setMobileOpen(false);
    setToast("");
    setError("");
    setAuthError("");
    setLoadedScope("");
    setFailedScope("");
    setRecordLoading(false);
  }, [section]);
  const acceptUser = useCallback(
    (nextUser: User) => {
      clearWorkspace();
      setUser(nextUser);
      router.replace("/dashboard");
    },
    [clearWorkspace, router],
  );
  const stages = pipelines.flatMap((p) => p.stages);
  const activePipeline = pipelines.find(p => p.id === selectedPipeline) ?? pipelines[0];
  // A deep-linked deal keeps its own pipeline even when a different board is selected.
  const editorPipeline = editor && editor !== "new" && editor.pipeline_id
    ? pipelines.find(pipeline => pipeline.id === text(editor.pipeline_id))
    : activePipeline;
  const pipelineScope = section === "deals" ? activePipeline?.id ?? "" : "";
  const notify = useCallback((message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 4000);
  }, []);
  // Reset route-local controls before React commits the next section.
  // Authentication persists; loaded records are scoped to their exact request.
  if (previousRoute.section !== section || previousRoute.routeQuery !== routeQuery) {
    setPreviousRoute({ section, routeQuery });
    setQuery(routeQuery ?? "");
    setPage(0);
    setFilter("");
    setSort(`${sortDateField(section)}:desc`);
    setEditor(null);
    setError("");
    setToast("");
    setFailedScope("");
    setLoadedScope("");
    setRecordLoading(Boolean(activeRecordId && singular[section]));
  }
  if (previousRecordId !== activeRecordId) {
    setPreviousRecordId(activeRecordId);
    setEditor(null);
    setError("");
    setRecordLoading(Boolean(activeRecordId && singular[section]));
  }
  const scope = JSON.stringify([user?.org_id, user?.id, section, page, query, filter, sort, pipelineScope]);
  const contentPending = loadedScope !== scope && failedScope !== scope;
  const contentFailed = failedScope === scope;
  const activeScope = useRef(scope);
  useEffect(() => {
    activeScope.current = scope;
  }, [scope]);
  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch((failure) => {
        if (failure instanceof ApiError && failure.status === 401)
          setUser(null);
        else setAuthError((failure as Error).message);
      })
      .finally(() => setAuthLoading(false));
  }, []);
  useEffect(() => {
    const expired = () => {
      clearWorkspace();
      setUser(null);
    };
    window.addEventListener("relay:session-expired", expired);
    return () => window.removeEventListener("relay:session-expired", expired);
  }, [clearWorkspace]);
  useEffect(() => {
    if (!user) return;
    const id = activeRecordId;
    let active = true;
    if (id && singular[section])
      api<Row>(`/${entityFor(section)}/${encodeURIComponent(id)}`)
        .then((record) => {
          if (active) {
            setEditor(record);
            setRecordLoading(false);
          }
        })
        .catch((failure) => {
          if (active) {
            setError((failure as Error).message);
            setRecordLoading(false);
          }
        });
    return () => {
      active = false;
    };
  }, [user, section, activeRecordId, routeQuery]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        setSearchOpen((open) => !open);
      }
      if (event.key === "Escape") {
        setSearchOpen(false);
        setMobileOpen(false);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
  const load = useCallback(async () => {
    if (!user || activeScope.current !== scope) return;
    const sequence = ++requestSequence.current;
    setLoading(true);
    setError("");
    setFailedScope("");
    try {
      if (["dashboard", "reports"].includes(section)) {
        const [stats, taskList, dealList, pipelineList] = await Promise.all([
          api<Record<string, unknown>>("/dashboard"),
          api<List>(
            "/activities?limit=6&status=pending&sort=due_date&order=asc",
          ),
          api<List>("/deals?limit=6"),
          api<{ items: Pipeline[] }>("/pipelines"),
        ]);
        if (sequence !== requestSequence.current) return;
        setDashboard(stats);
        setTasks(taskList.items);
        setRecentDeals(dealList.items);
        setPipelines(pipelineList.items);
      } else if (["workbench", "pipelines", "calendar"].includes(section)) {
        // These views own their bounded server queries.
      } else if (section === "settings") {
        const integrations = await api<List>("/integrations");
        if (sequence !== requestSequence.current) return;
        setRows(integrations.items ?? []);
      } else {
        const params = new URLSearchParams({
          limit: "20",
          offset: String(page * 20),
          q: query,
        });
        if (filter) params.set("status", filter);
        if (pipelineScope) params.set("pipeline_id", pipelineScope);
        params.set("sort", sort.split(":")[0] ?? "updated_at");
        params.set("order", sort.split(":")[1] ?? "desc");
        const result = await api<List>(`/${entityFor(section)}?${params}`);
        if (sequence !== requestSequence.current) return;
        setRows(result.items ?? []);
        setTotal(result.total ?? result.items?.length ?? 0);
        if (section === "deals") {
          const data = await api<{ items: Pipeline[] }>("/pipelines");
          if (sequence !== requestSequence.current) return;
          setPipelines(data.items);
        }
      }
      setWorkspaceRevision(value => value + 1);
      setLoadedScope(scope);
      setFailedScope("");
    } catch (failure) {
      if (sequence === requestSequence.current) {
        setError((failure as Error).message);
        setFailedScope(scope);
      }
    } finally {
      if (sequence === requestSequence.current) setLoading(false);
    }
  }, [user, section, page, query, filter, sort, scope, pipelineScope]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 180);
    return () => {
      window.clearTimeout(timer);
      requestSequence.current += 1;
    };
  }, [load]);
  async function mutate(path: string, payload: unknown, method = "PATCH") {
    try {
      await api(path, { method, body: JSON.stringify(payload) });
      if (activeScope.current !== scope) return;
      notify("Saved successfully");
      await load();
    } catch (failure) {
      if (activeScope.current === scope) setError((failure as Error).message);
    }
  }
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST", body: "{}" });
      clearWorkspace();
      setUser(null);
      router.push("/dashboard");
    } catch (failure) {
      setError((failure as Error).message);
    }
  }
  if (authLoading)
    return (
      <div className="loading-screen">
        <div className="brand-mark">r</div>
        <p>Opening your workspace…</p>
      </div>
    );
  if (authError)
    return (
      <main className="loading-screen">
        <h1>Workspace unavailable</h1>
        <p role="alert">{authError}</p>
        <button
          className="button primary"
          onClick={() => window.location.reload()}
        >
          Try again
        </button>
      </main>
    );
  if (!user) return <Auth onSuccess={acceptUser} />;
  const title = navigation.find(([key]) => key === section)?.[1] ?? (section === "pipelines" ? "Pipeline settings" : "Workspace");
  const name = user.name.split(" ")[0];
  return (
    <div className="workspace">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      {mobileOpen && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <Link href="/dashboard" className="brand">
          <span className="brand-mark">r</span>relay
          <span className="brand-dot">.</span>
        </Link>
        <div className="workspace-name">
          <div className="workspace-avatar">{initials(user.company_name)}</div>
          <div>
            <strong>{user.company_name}</strong>
            <span>Your workspace</span>
          </div>
        </div>
        <nav aria-label="Main navigation">
          {navigation.map(([key, textValue], index) => (
            <div key={key}>
              {[1, 5, 9].includes(index) && <div className="nav-divider" />}
              <Link
                onClick={() => setMobileOpen(false)}
                className={`nav-link ${section === key ? "active" : ""}`}
                href={`/${key}`}
                aria-current={section === key ? "page" : undefined}
              >
                <Icon
                  name={
                    key === "automations"
                      ? "settings"
                      : key === "communications"
                        ? "mail"
                        : key
                  }
                  size={18}
                />
                <span>{textValue}</span>
                {section === key && <span className="active-dot" />}
              </Link>
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="avatar">{initials(user.name)}</div>
          <div className="user-copy">
            <strong>{user.name}</strong>
            <span>{user.role}</span>
          </div>
          <button
            aria-label="Sign out"
            title="Sign out"
            className="icon-button"
            onClick={() => void logout()}
          >
            <Icon name="logout" size={18} />
          </button>
        </div>
      </aside>
      <div className="workspace-main">
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMobileOpen(true)}
            >
              <Icon name="menu" />
            </button>
            <span>Workspace</span>
            <span className="crumb-separator">/</span>
            <strong>{title}</strong>
          </div>
          <div className="topbar-actions">
            <button
              className="global-search"
              aria-label="Search anything"
              onClick={() => setSearchOpen(true)}
            >
              <Icon name="search" size={17} />
              <span>Search anything</span>
              <kbd>⌘ K</kbd>
            </button>
            <Notifications />
            <span className="topbar-avatar" title={user.name}>
              {initials(user.name)}
            </span>
          </div>
        </header>
        <main className="content" id="main-content">
          {recordLoading && <p role="status">Opening record…</p>}
          {error && (
            <div role="alert" className="error-banner">
              <span>{error}</span>
              <button onClick={() => void load()}>Try again</button>
            </div>
          )}
          {section === "dashboard" ? (
            <>
              {["Owner", "Admin"].includes(user.role) && (
                <SampleData
                  onLoaded={() => {
                    notify(
                      "Sample workspace loaded — all records are fictional",
                    );
                    void load();
                  }}
                />
              )}
              <div className="page-heading">
                <div>
                  <h1>
                    Good{" "}
                    {new Date().getHours() < 12
                      ? "morning"
                      : new Date().getHours() < 17
                        ? "afternoon"
                        : "evening"}
                    , {name}.
                  </h1>
                  <p>Let’s make the next conversation count.</p>
                </div>
                <div className="heading-actions">
                  <span className="today-label">
                    <Icon name="calendar" size={17} />
                    {new Intl.DateTimeFormat("en-IN", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    }).format(new Date())}
                  </span>
                  <button
                    className="button primary"
                    disabled={!canWrite}
                    onClick={() => router.push("/leads?new=1")}
                  >
                    <Icon name="plus" size={17} />
                    Add lead
                  </button>
                </div>
              </div>
              {contentPending ? <SectionLoading title={title} /> : contentFailed ? null : <Dashboard
                data={dashboard}
                tasks={tasks}
                deals={recentDeals}
                stages={stages}
                loading={loading}
                readonly={!canWrite}
                onComplete={(task) =>
                  void mutate(`/activities/${task.id}`, { status: "completed" })
                }
              />}
            </>
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <h1>{title}</h1>
                  <p>{descriptions[section]}</p>
                </div>
                <div className="heading-actions">
                  {section === "deals" && <Link className="button secondary" href="/pipelines"><Icon name="settings" size={17}/> Configure pipelines</Link>}
                  {section === "pipelines" && <Link className="button subtle" href="/deals">Back to pipeline</Link>}
                  {canWrite && singular[section] && (
                    <button
                      className="button primary"
                      onClick={() => setEditor("new")}
                    >
                      <Icon name="plus" size={17} />
                      {section === "communications"
                        ? "Compose email"
                        : `Add ${singular[section]}`}
                    </button>
                  )}
                </div>
              </div>
              {section === "workbench" ? <SalesWorkbench userId={user.id} canWrite={canWrite} onChanged={() => void load()}/> : section === "pipelines" ? <PipelineSettings canWrite={canWrite && ["Owner", "Admin", "Sales Manager"].includes(user.role)} onChanged={() => void load()}/> : ["reports", "settings"].includes(section) && contentPending ? <SectionLoading title={title} /> : ["reports", "settings"].includes(section) && contentFailed ? null : section === "reports" ? (
                <Reports data={dashboard} stages={stages} deals={recentDeals} />
              ) : section === "settings" ? (
                <Settings
                  user={user}
                  integrations={rows}
                  onUser={setUser}
                  notify={notify}
                />
              ) : (
                <>
                  {section === "communications" && (
                    <EmailTemplates readonly={!canWrite} />
                  )}
                  {section === "automations" && <AutomationRuns />}
                  <div className="toolbar">
                    <div className="table-search">
                      <Icon name="search" size={17} />
                      <input
                        aria-label={`Search ${title.toLowerCase()}`}
                        placeholder={`Search ${title.toLowerCase()}…`}
                        value={query}
                        onChange={(event) => {
                          setQuery(event.target.value);
                          setPage(0);
                        }}
                      />
                    </div>
                    <div className="toolbar-right">
                      {section !== "calendar" && !(section === "deals" && view === "board") && <Select
                        aria-label="Sort records"
                        value={sort}
                        onChange={(event) => {
                          setSort(event.target.value);
                          setPage(0);
                        }}
                      >
                        <option value={`${sortDateField(section)}:desc`}>
                          {sortDateField(section) === "created_at" ? "Newest created" : "Recently updated"}
                        </option>
                        <option value={`${sortDateField(section)}:asc`}>{sortDateField(section) === "created_at" ? "Oldest created" : "Oldest updated"}</option>
                        <option value="name:asc">Name: A to Z</option>
                        <option value="name:desc">Name: Z to A</option>
                      </Select>}
                      {!(section === "deals" && view === "board") && fields[normalized]?.find(
                        (field) => field.key === "status",
                      )?.options && (
                        <Select
                          aria-label="Filter by status"
                          value={filter}
                          onChange={(event) => {
                            setFilter(event.target.value);
                            setPage(0);
                          }}
                        >
                          <option value="">All statuses</option>
                          {fields[normalized]
                            ?.find((field) => field.key === "status")
                            ?.options?.map((option) => (
                              <option key={option}>{option}</option>
                            ))}
                        </Select>
                      )}
                      {section === "deals" && pipelines.length > 0 && <Select aria-label="Sales pipeline" value={activePipeline?.id ?? ""} onChange={event => { setSelectedPipeline(event.target.value); setPage(0); }}>{pipelines.map(pipeline => <option key={pipeline.id} value={pipeline.id}>{pipeline.name}</option>)}</Select>}
                      {section === "deals" && (
                        <div className="segmented">
                          <button
                            className={view === "board" ? "selected" : ""}
                            onClick={() => { setView("board"); setFilter(""); setPage(0); }}
                          >
                            Board
                          </button>
                          <button
                            className={view === "table" ? "selected" : ""}
                            onClick={() => setView("table")}
                          >
                            Table
                          </button>
                        </div>
                      )}
                      {!["automations", "communications"].includes(section) && (
                        <ImportExport
                          key={section}
                          readonly={!canWrite}
                          entity={entityFor(section)}
                          query={query}
                          status={filter}
                          sort={sort}
                          pipelineId={section === "deals" ? activePipeline?.id : undefined}
                          onImport={() => {
                            notify("Import finished");
                            void load();
                          }}
                        />
                      )}
                    </div>
                  </div>
                  {section === "calendar" ? <CalendarView query={query} status={filter} revision={workspaceRevision} canWrite={canWrite} onSelect={setEditor} onCreate={date => setEditor({ id: "", due_date: date })}/> : section === "deals" && view === "board" && activePipeline ? <PipelineBoard key={`${activePipeline.id}-${query}`} pipelineId={activePipeline.id} stages={activePipeline.stages} query={query} revision={workspaceRevision} canWrite={canWrite} onOpen={setEditor} onCreate={stageId => setEditor({ id: "", stage_id: stageId, pipeline_id: activePipeline.id })} onChanged={() => { notify("Deal stage updated"); void load(); }}/> : contentPending ? (
                    <SectionLoading title={title} />
                  ) : contentFailed ? null : rows.length === 0 ? (
                    <Empty
                      title={
                        query || filter
                          ? "No matching records"
                          : section === "activities" ? "Your tasks start here" : `Your ${title.toLowerCase()} start here`
                      }
                      detail={
                        query || filter
                          ? "Try a different search or status filter."
                          : `Add your first ${singular[section] ?? "record"} to get things moving.`
                      }
                      action={
                        query || filter || !canWrite
                          ? undefined
                          : () => setEditor("new")
                      }
                    />
                  ) : (
                    <DataTable
                      rows={rows}
                      columns={columns[normalized] ?? ["name", "status"]}
                      stages={stages}
                      onSelect={setEditor}
                      onComplete={
                        canWrite && normalized === "activities"
                          ? (row) =>
                              void mutate(`/activities/${row.id}`, {
                                status:
                                  row.status === "completed"
                                    ? "pending"
                                    : "completed",
                              })
                          : undefined
                      }
                    />
                  )}
                  {!contentPending && !contentFailed && section !== "calendar" && !(section === "deals" && view === "board") && <div className="pagination">
                    <span>
                      {total
                        ? `${page * 20 + 1}–${Math.min(page * 20 + 20, total)} of ${total} records`
                        : "0 records"}
                    </span>
                    <div>
                      <button
                        className="button subtle"
                        disabled={page === 0}
                        onClick={() => setPage(page - 1)}
                      >
                        Previous
                      </button>
                      <button
                        className="button subtle"
                        disabled={(page + 1) * 20 >= total}
                        onClick={() => setPage(page + 1)}
                      >
                        Next
                      </button>
                    </div>
                  </div>}
                </>
              )}
            </>
          )}
        </main>
        <footer className="app-footer">
          <span>Built for better relationships.</span>
          <span>Relay CRM</span>
        </footer>
      </div>
      {editor && (
        <Editor
          user={user}
          readonly={!canWrite}
          key={`editor:${normalized}:${editor === "new" ? "new" : editor.id || "new"}`}
          section={normalized}
          record={editor}
          stages={normalized === "deals" ? editorPipeline?.stages ?? [] : stages}
          pipelineId={editorPipeline?.id}
          onClose={() => setEditor(null)}
          onSaved={() => {
            setEditor(null);
            notify("Your changes are saved");
            void load();
          }}
        />
      )}
      {searchOpen && <GlobalSearch onClose={() => setSearchOpen(false)} />}
      {toast && (
        <div className="toast" role="status">
          <Icon name="check" size={18} />
          {toast}
        </div>
      )}
      <AutoCreate
        key={`auto-create:${section}:${routeSearch.get("new") ?? ""}`}
        onCreate={() => {
          if (canWrite) {
            const params = new URLSearchParams(window.location.search);
            const defaults: Row = { id: "" };
            for (const key of ["party_id", "contact_id", "entity_type", "entity_id", "due_date", "stage_id", "pipeline_id"]) {
              const value = params.get(key); if (value) defaults[key] = value;
            }
            setEditor(Object.keys(defaults).length > 1 ? defaults : "new");
          }
        }}
      />
    </div>
  );
}

function AutoCreate({ onCreate }: { onCreate: () => void }) {
  const done = useRef(false);
  useEffect(() => {
    if (
      !done.current &&
      new URLSearchParams(window.location.search).get("new") === "1"
    ) {
      done.current = true;
      onCreate();
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [onCreate]);
  return null;
}
function Auth({ onSuccess }: { onSuccess: (user: User) => void }) {
  const signupRequested = useSearchParams().get("signup") === "1";
  const [signup, setSignup] = useState(false);
  const [signupEnabled, setSignupEnabled] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    api<{ signup_enabled: boolean }>("/auth/options")
      .then((options) => {
        setSignupEnabled(options.signup_enabled);
        setSignup(options.signup_enabled && signupRequested);
      })
      .catch((failure) => setError((failure as Error).message));
  }, [signupRequested]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      onSuccess(
        await api<User>(signup ? "/auth/signup" : "/auth/login", {
          method: "POST",
          body: JSON.stringify(data),
        }),
      );
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-layout">
      <section className="auth-story">
        <div className="brand">
          <span className="brand-mark">r</span>relay
          <span className="brand-dot">.</span>
        </div>
        <div>
          <h1>
            Good business.
            <br />
            Great relationships.
          </h1>
          <p>
            A calmer place to manage your pipeline, keep your promises, and move
            your business forward.
          </p>
          <div className="auth-rule" />
          <span>Every conversation has a next step.</span>
        </div>
        <p className="auth-caption">
          Your people. Your pipeline. One workspace.
        </p>
      </section>
      <section className="auth-form-side">
        <form className="auth-form" onSubmit={(event) => void submit(event)}>
          <h2>{signup ? "Start your next chapter." : "Welcome back."}</h2>
          <p>
            {signup
              ? "Create a workspace for your business."
              : "Sign in to pick up where you left off."}
          </p>
          {error && (
            <div role="alert" className="form-error">
              {error}
            </div>
          )}
          {signup && (
            <>
              <label>
                Your name
                <input
                  name="name"
                  required
                  autoComplete="name"
                  placeholder="Arjun Sharma"
                />
              </label>
              <label>
                Company name
                <input
                  name="company_name"
                  required
                  autoComplete="organization"
                  placeholder="Your company"
                />
              </label>
            </>
          )}
          <label>
            Work email
            <input
              name="email"
              type="email"
              required
              autoComplete="email"
              placeholder="you@company.com"
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              required
              minLength={signup ? 8 : undefined}
              autoComplete={signup ? "new-password" : "current-password"}
              placeholder={
                signup ? "At least 8 characters" : "Enter your password"
              }
            />
          </label>
          <button className="button primary auth-submit" disabled={busy}>
            {busy ? "Please wait…" : signup ? "Create workspace" : "Sign in"}
            <Icon name="arrow" size={17} />
          </button>
          {signupEnabled ? (
            <p className="auth-toggle">
              {signup ? "Already have a workspace?" : "New to Relay?"}{" "}
              <button
                type="button"
                onClick={() => {
                  setSignup(!signup);
                  setError("");
                }}
              >
                {signup ? "Sign in" : "Create a workspace"}
              </button>
            </p>
          ) : signupEnabled === false ? (
            <p className="auth-toggle">
              Need access? Ask your administrator for an invitation link.
            </p>
          ) : null}
        </form>
        <span className="auth-privacy">
          Your business data stays in your workspace.
        </span>
      </section>
    </div>
  );
}

function Dashboard({
  data,
  tasks,
  deals,
  stages,
  loading,
  readonly,
  onComplete,
}: {
  data: Record<string, unknown>;
  tasks: Row[];
  deals: Row[];
  stages: Stage[];
  loading: boolean;
  readonly: boolean;
  onComplete: (row: Row) => void;
}) {
  const metrics = (data.metrics ?? data) as Record<string, unknown>;
  const pipeline = (data.stages ?? []) as Row[];
  const metricsList = [
    {
      label: "Open pipeline",
      value: amount(
        metrics.pipeline_value ??
          metrics.open_pipeline_value ??
          metrics.open_pipeline ??
          0,
      ),
      hint: "Potential revenue",
      route: "/deals",
    },
    {
      label: "Total leads",
      value: text(
        (data.counts as Record<string, unknown> | undefined)?.leads ?? 0,
      ),
      hint: "All lead records",
      route: "/leads",
    },
    {
      label: "Won revenue",
      value: amount(metrics.won_revenue ?? metrics.won_value ?? 0),
      hint: "Closed and celebrated",
      route: "/deals",
    },
    {
      label: "Overdue tasks",
      value: text(metrics.overdue_tasks ?? 0),
      hint: "Need your attention",
      route: "/activities",
    },
  ];
  return (
    <>
      <div className="metrics-strip" aria-busy={loading}>
        {metricsList.map((metric) => (
          <Link href={metric.route} key={metric.label} className="metric">
            <span>
              {metric.label}
              <Icon name="arrow" size={16} />
            </span>
            <strong>{!Object.keys(data).length ? "—" : metric.value}</strong>
            <small>{metric.hint}</small>
          </Link>
        ))}
      </div>
      <div className="dashboard-grid">
        <section className="panel pipeline-panel">
          <div className="panel-heading">
            <div>
              <h2>Your pipeline, at a glance</h2>
              <p>Every opportunity has somewhere to go.</p>
            </div>
            <Link href="/deals" className="text-link">
              View pipeline
              <Icon name="arrow" size={15} />
            </Link>
          </div>
          <div className="pipeline-chart">
            {(pipeline.length
              ? pipeline
              : stages.map((stage): Row => ({
                  id: stage.id,
                  stage_id: stage.id,
                  name: stage.name,
                  count: 0,
                  amount: 0,
                }))
            )
              .filter((row) => !["won", "lost"].includes(text(row.category)))
              .map((row, index, array) => {
                const value = Number(row.amount ?? row.value ?? row.total ?? 0);
                const maximum = Math.max(
                  ...array.map((item) =>
                    Number(item.amount ?? item.value ?? item.total ?? 0),
                  ),
                  1,
                );
                return (
                  <div className="pipeline-chart-row" key={row.id ?? index}>
                    <span className="pipeline-label">
                      {text(row.name ?? row.stage_name)}
                    </span>
                    <div className="pipeline-track">
                      <div
                        style={{
                          width: `${Math.max(value ? 4 : 0, (value / maximum) * 100)}%`,
                          background: [
                            "#255746",
                            "#43715c",
                            "#6f9480",
                            "#9ab39d",
                            "#bacab5",
                          ][index % 5],
                        }}
                      />
                    </div>
                    <span className="pipeline-amount">{amount(value)}</span>
                    <span className="pipeline-count">
                      {text(row.count ?? 0)}
                    </span>
                  </div>
                );
              })}
            {!pipeline.length && !stages.length && (
              <p className="quiet-empty">
                Create a deal to start your pipeline.
              </p>
            )}
          </div>
          <div className="panel-bottom">
            <span>
              <span className="legend-dot" />
              Open opportunities
            </span>
            <span>Values in INR</span>
          </div>
        </section>
        <section className="panel task-panel">
          <div className="panel-heading">
            <div>
              <h2>A little focus, a lot of progress</h2>
              <p>Your next follow-ups and to-dos.</p>
            </div>
            <Link href="/activities" className="text-link">
              View all
            </Link>
          </div>
          <div className="task-list">
            {tasks.slice(0, 5).map((task) => (
              <div className="task-row" key={task.id}>
                <button
                  className="task-checkbox"
                  disabled={readonly}
                  aria-label={`Complete ${text(task.name)}`}
                  onClick={() => onComplete(task)}
                />
                <div>
                  <Link href={`/activities?id=${encodeURIComponent(task.id)}`}>{text(task.name)}</Link>
                  <span>
                    {text(task.type) || "Task"}{" "}
                    {task.due_date
                      ? `· ${text(task.due_date).slice(0, 10)}`
                      : ""}
                  </span>
                </div>
                {task.priority === "high" && (
                  <span className="priority-dot" title="High priority" />
                )}
              </div>
            ))}
            {!tasks.length && (
              <div className="compact-empty">
                <Icon name="check" size={24} />
                <strong>A little breathing room.</strong>
                <p>No pending tasks. Plan your next follow-up.</p>
              </div>
            )}
          </div>
          <Link
            href={readonly ? "/activities" : "/activities?new=1"}
            className="add-task"
          >
            <Icon name="plus" size={16} />
            Add a task
          </Link>
        </section>
      </div>
      <section className="panel recent-panel">
        <div className="panel-heading">
          <div>
            <h2>Conversations moving forward</h2>
            <p>Your recently updated opportunities.</p>
          </div>
          <Link href="/deals" className="text-link">
            All deals
            <Icon name="arrow" size={15} />
          </Link>
        </div>
        {deals.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Opportunity</th>
                  <th>Value</th>
                  <th>Stage</th>
                  <th>Expected close</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {deals.slice(0, 5).map((deal) => (
                  <tr key={deal.id}>
                    <td>
                      <Link href={`/deals?id=${encodeURIComponent(deal.id)}`} className="record-name">
                        <span className="record-monogram">
                          {initials(text(deal.name))}
                        </span>
                        {text(deal.name)}
                      </Link>
                    </td>
                    <td className="numeric">{amount(deal.amount)}</td>
                    <td>
                      {stages.find((stage) => stage.id === deal.stage_id)
                        ?.name ?? "—"}
                    </td>
                    <td>
                      {text(deal.expected_close_date).slice(0, 10) || "Not set"}
                    </td>
                    <td>
                      <Badge value={deal.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="quiet-empty">
            Your first opportunity is a good place to start.{" "}
            {!readonly && <Link href="/deals?new=1">Add a deal</Link>}
          </div>
        )}
      </section>
    </>
  );
}
function DataTable({
  rows,
  columns: visible,
  stages,
  onSelect,
  onComplete,
}: {
  rows: Row[];
  columns: string[];
  stages: Stage[];
  onSelect: (row: Row) => void;
  onComplete?: (row: Row) => void;
}) {
  return (
    <div className="table-wrap">
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {onComplete && (
                <th className="check-column">
                  <span className="sr-only">Completion</span>
                </th>
              )}
              {visible.map((column) => (
                <th key={column}>{label(column)}</th>
              ))}
              <th>
                <span className="sr-only">Open record</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                {onComplete && (
                  <td>
                    <button
                      className={`task-checkbox ${row.status === "completed" ? "checked" : ""}`}
                      aria-label={`${row.status === "completed" ? "Reopen" : "Complete"} ${text(row.name)}`}
                      onClick={() => onComplete(row)}
                    >
                      {row.status === "completed" && (
                        <Icon name="check" size={13} />
                      )}
                    </button>
                  </td>
                )}
                {visible.map((column, index) => (
                  <td key={column}>
                    {index === 0 ? (
                      <button
                        className="record-name"
                        onClick={() => onSelect(row)}
                      >
                        {!onComplete && (
                          <span className="record-monogram">
                            {initials(text(row[column]))}
                          </span>
                        )}
                        <span>
                          {text(row[column]) || "Untitled"}
                          {Boolean(row.email) && column === "name" && (
                            <small>{text(row.email)}</small>
                          )}
                        </span>
                      </button>
                    ) : ["status", "priority"].includes(column) ? (
                      <Badge value={row[column]} />
                    ) : ["value", "amount", "budget", "spent"].includes(
                        column,
                      ) ? (
                      <span className="numeric">{amount(row[column])}</span>
                    ) : column === "stage_id" ? (
                      (stages.find((stage) => stage.id === row.stage_id)
                        ?.name ?? "—")
                    ) : column === "email" && row.email ? (
                      <a
                        className="subtle-link"
                        href={`mailto:${text(row.email)}`}
                      >
                        {text(row.email)}
                      </a>
                    ) : column === "phone" && row.phone ? (
                      <a
                        className="subtle-link"
                        href={`tel:${text(row.phone)}`}
                      >
                        {text(row.phone)}
                      </a>
                    ) : column.endsWith("_at") ? (
                      formatTimestamp(row[column])
                    ) : column.endsWith("_date") ||
                      column === "next_follow_up" ? (
                      text(row[column]).slice(0, 10) || "—"
                    ) : column === "enabled" ? (
                      <Badge value={row.enabled ? "Active" : "Paused"} />
                    ) : (
                      text(row[column]) || "—"
                    )}
                  </td>
                ))}
                <td>
                  <button
                    className="icon-button"
                    aria-label={`Open ${text(row.name ?? row.subject)}`}
                    onClick={() => onSelect(row)}
                  >
                    <Icon name="arrow" size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
function Editor({
  user,
  section,
  readonly,
  record,
  stages,
  pipelineId,
  onClose,
  onSaved,
}: {
  user: User;
  section: string;
  readonly: boolean;
  record: Row | "new";
  stages: Stage[];
  pipelineId?: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const router = useRouter();
  const initial: Record<string, unknown> = record === "new" ? {} : record;
  const id = text(initial.id);
  const converted = section === "leads" && initial.status === "Converted";
  const locked = readonly || converted;
  const dialogRef = useRef<HTMLElement | null>(null);
  useDialogKeyboard(dialogRef, onClose);
  const [values, setValues] = useState<Record<string, unknown>>(initial);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("details");
  const [timeline, setTimeline] = useState<Row[]>([]);
  const [reason, setReason] = useState("");
  const [losing, setLosing] = useState(false);
  const [members, setMembers] = useState<User[]>([]);
  const assignmentSupported = !["automations", "communications"].includes(section);
  const ownRecordsOnly = ["Sales Rep", "Sales Representative"].includes(user.role);
  const selectedOwner = !id && values.owner_id === undefined ? user.id : text(values.owner_id);
  const formRef = useRef<HTMLFormElement>(null);
  const requestKey = useRef<{ fingerprint: string; key: string } | null>(null);
  useEffect(() => {
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = old;
    };
  }, []);
  useEffect(() => {
    formRef.current
      ?.querySelector<HTMLInputElement>("input:not(:disabled)")
      ?.focus();
  }, []);
  useEffect(() => {
    if (!assignmentSupported) return;
    let active = true;
    api<User[]>("/team").then((result) => {
      if (active) setMembers(result.filter(member => member.is_active && (!ownRecordsOnly || member.id === user.id)));
    }).catch((failure) => { if (active) setError((failure as Error).message); });
    return () => { active = false; };
  }, [assignmentSupported, ownRecordsOnly, user.id]);
  async function action(path: string, body: unknown = {}, method = "POST") {
    setBusy(true);
    setError("");
    try {
      const fingerprint = JSON.stringify({ path, method, body });
      if (requestKey.current?.fingerprint !== fingerprint)
        requestKey.current = { fingerprint, key: crypto.randomUUID() };
      await api(path, {
        method,
        body: body === undefined ? undefined : JSON.stringify(body),
        headers: { "Idempotency-Key": requestKey.current.key },
      });
      onSaved();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    const submitted = formRef.current ? new FormData(formRef.current) : null;
    const payload: Record<string, unknown> = {};
    for (const field of fields[section] ?? []) {
      // Native date pickers/autofill can update their DOM value without a React
      // change event. Submit the actual named date control, including clearing it.
      const value = field.type === "date" && submitted?.has(field.key)
        ? submittedDate(text(submitted.get(field.key)), initial[field.key]) : values[field.key];
      if (value !== undefined)
        payload[field.key] =
          value === "" && field.type === "number"
            ? "0"
            : value === "" &&
                (field.type === "date" ||
                  field.type?.startsWith("relation:") ||
                  field.key === "entity_type")
              ? null
              : value;
      else if (!id && field.options)
        payload[field.key] = field.options[0] || null;
    }
    if (id && initial.version) payload.version = initial.version;
    if (assignmentSupported && values.owner_id !== undefined) payload.owner_id = values.owner_id;
    if (section === "automations") {
      delete payload.version;
      payload.conditions = values.conditions ?? [];
      payload.action_text =
        text(values.action_text) || "Follow up with {{name}}";
      payload.enabled = id ? Boolean(initial.enabled) : true;
      if (payload.due_days !== undefined)
        payload.due_days = Number(payload.due_days);
    }
    if (section === "deals") {
      payload.pipeline_id = initial.pipeline_id || pipelineId;
      payload.stage_id = payload.stage_id || stages.find(stage => stage.category === "open")?.id;
      if (!payload.pipeline_id || !stages.some(stage => stage.id === payload.stage_id)) {
        setError("Choose a stage from this deal’s pipeline. If stages have changed, close the form and reopen it.");
        return;
      }
    }
    await action(
      `/${entityFor(section)}${id ? `/${id}` : ""}`,
      payload,
      id ? "PATCH" : "POST",
    );
  }
  async function loadTimeline() {
    setTab("timeline");
    try {
      const result = await api<{ items: Row[] }>(
        `/${entityFor(section)}/${id}/timeline`,
      );
      setTimeline(result.items ?? []);
    } catch (failure) {
      setError((failure as Error).message);
    }
  }
  return (
    <div className="drawer-overlay">
      <button
        className="drawer-scrim"
        aria-label="Close record"
        onClick={onClose}
      />
      <aside
        ref={dialogRef}
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="editor-title"
      >
        <header className="drawer-header">
          <div>
            <span className="drawer-type">{singular[section] ?? "Record"}</span>
            <h2 id="editor-title">
              {id
                ? text(initial.name || initial.subject)
                : `New ${singular[section] ?? "record"}`}
            </h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close record"
            onClick={onClose}
          >
            <Icon name="close" />
          </button>
        </header>
        {id && (
          <div className="drawer-tabs">
            <button
              className={tab === "details" ? "active" : ""}
              onClick={() => setTab("details")}
            >
              Details
            </button>
            {["accounts", "contacts"].includes(section) && <button className={tab === "context" ? "active" : ""} onClick={() => setTab("context")}>Customer overview</button>}
            {section === "campaigns" && <button className={tab === "members" ? "active" : ""} onClick={() => setTab("members")}>Members</button>}
            {!["automations", "communications"].includes(section) && (
              <button
                className={tab === "timeline" ? "active" : ""}
                onClick={() => void loadTimeline()}
              >
                Activity & history
              </button>
            )}
          </div>
        )}
        {error && (
          <div role="alert" className="form-error drawer-error">
            {error}
          </div>
        )}
        {tab === "context" && ["accounts", "contacts"].includes(section) ? <div className="drawer-body"><CustomerContext entity={section === "accounts" ? "parties" : "contacts"} entityId={id} refreshKey={text(initial.version)} onCreate={locked ? undefined : (target, defaults) => { onClose(); router.push(`/${target}?${new URLSearchParams({ new: "1", ...defaults })}`); }}/></div> : tab === "members" && section === "campaigns" ? <div className="drawer-body"><CampaignMembers campaignId={id} canEdit={!locked} refreshKey={text(initial.version)}/></div> : tab === "timeline" ? (
          <div className="drawer-body">
            <div className="timeline">
              {timeline.length ? (
                timeline.map((entry) => (
                  <article key={entry.id}>
                    <span className="timeline-point" />
                    <strong>
                      {text(entry.action ?? entry.name ?? entry.type)}
                    </strong>
                    <p>
                      {text(entry.description ?? entry.message ?? entry.notes)}
                    </p>
                    <small>
                      {formatTimestamp(entry.created_at)}
                    </small>
                  </article>
                ))
              ) : (
                <p className="muted">No recorded activity yet.</p>
              )}
            </div>
          </div>
        ) : (
          <form
            ref={formRef}
            onSubmit={(event) => void save(event)}
            className="editor-form"
          >
            <div className="drawer-body">
              {converted && (
                <div className="converted-message">
                  <h3>Lead converted</h3>
                  <p>
                    This record is preserved as read-only. Continue working in
                    the connected records.
                  </p>
                  <div className="related-links">
                    {[
                      ["converted_contact_id", "contacts", "Contact"],
                      ["converted_party_id", "accounts", "Company"],
                      ["converted_deal_id", "deals", "Deal"],
                    ].map(([key, route, title]) =>
                      initial[key ?? ""] ? (
                        <Link
                          className="button secondary"
                          key={key}
                          href={`/${route}?id=${text(initial[key ?? ""])}`}
                        >
                          {title}
                          <Icon name="arrow" size={14} />
                        </Link>
                      ) : null,
                    )}
                  </div>
                </div>
              )}
              {readonly && (
                <p className="form-error">
                  Your role has view-only access to this record.
                </p>
              )}
              <fieldset disabled={locked}>
                <div className="form-grid">
                  {(fields[section] ?? []).map((field) => (
                    <label
                      className={field.wide ? "full-width" : ""}
                      key={field.key}
                    >
                      {field.label}
                      {field.required && <span className="required"> *</span>}
                      {field.type === "textarea" ? (
                        <textarea
                          rows={5}
                          value={text(values[field.key])}
                          onChange={(event) =>
                            setValues({
                              ...values,
                              [field.key]: event.target.value,
                            })
                          }
                          required={field.required}
                        />
                      ) : field.type?.startsWith("relation:") ? (
                        <RelationSelect
                          key={`${field.key}-${field.type === "relation:dynamic" ? text(values.entity_type) : field.type}`}
                          entity={
                            field.type === "relation:dynamic"
                              ? text(values.entity_type)
                              : (field.type.split(":")[1] ?? "")
                          }
                          value={text(values[field.key])}
                          onChange={(value) =>
                            setValues({ ...values, [field.key]: value })
                          }
                        />
                      ) : field.options || field.type === "stage" ? (
                        <Select
                          value={
                            text(values[field.key]) ||
                            (field.type === "stage"
                              ? stages.find(stage => stage.category === "open")?.id ?? ""
                              : field.options?.[0])
                          }
                          onChange={(event) =>
                            setValues({
                              ...values,
                              [field.key]: event.target.value,
                              ...(field.key === "entity_type"
                                ? { entity_id: "" }
                                : {}),
                            })
                          }
                        >
                          {field.type === "stage"
                            ? stages.map((stage) => (
                                <option value={stage.id} key={stage.id}>
                                  {stage.name}
                                </option>
                              ))
                            : field.options?.map((option) => (
                                <option key={option} value={option}>{option || "None"}</option>
                              ))}
                        </Select>
                      ) : (
                        <input
                          name={field.type === "date" ? field.key : undefined}
                          value={
                            field.type === "date"
                              ? text(values[field.key]).slice(0, 10)
                              : text(values[field.key])
                          }
                          type={field.type ?? "text"}
                          min={field.type === "number" ? "0" : undefined}
                          step={field.type === "number" ? "0.01" : undefined}
                          onChange={(event) =>
                            setValues({
                              ...values,
                              [field.key]: event.target.value,
                            })
                          }
                          required={field.required}
                        />
                      )}
                    </label>
                  ))}
                  {assignmentSupported && <label>
                    Assigned to
                    <Select aria-label="Assigned to" value={selectedOwner}
                      onChange={event => setValues({ ...values, owner_id: event.target.value || null })}>
                      {!ownRecordsOnly && <option value="">Unassigned</option>}
                      {selectedOwner && !members.some(member => member.id === selectedOwner) &&
                        <option value={selectedOwner}>{selectedOwner !== user.id ? "Current owner (inactive or unavailable)" : user.name}</option>}
                      {members.map(member => <option key={member.id} value={member.id}>{member.name}{member.id === user.id ? " (you)" : ""}</option>)}
                    </Select>
                  </label>}
                </div>
              </fieldset>
              {section === "automations" && !locked && (
                <AutomationConditions
                  value={(values.conditions ?? []) as Condition[]}
                  onChange={(conditions) =>
                    setValues({ ...values, conditions })
                  }
                />
              )}
              {section === "leads" && !locked && (
                <LeadDuplicates
                  id={id}
                  email={text(values.email)}
                  phone={text(values.phone)}
                  version={Number(initial.version) || undefined}
                  onMerged={onSaved}
                />
              )}
              {id && !["automations", "communications"].includes(section) && (
                <Attachments
                  entity={entityFor(section)}
                  recordId={id}
                  readonly={locked}
                />
              )}
              {id && section === "tickets" && (
                <TicketConversation ticketId={id} readonly={readonly} />
              )}
              {id &&
                !locked &&
                section === "leads" &&
                initial.status !== "Converted" && (
                  <section className="context-action">
                    <h3>Ready for the next step?</h3>
                    <p>
                      Convert this lead into a contact, company, and deal. Their
                      details stay connected.
                    </p>
                    <button
                      type="button"
                      className="button secondary"
                      disabled={busy}
                      onClick={() =>
                        void action(`/leads/${id}/convert`, {
                          create_deal: true,
                          amount: text(values.value || "0"),
                        })
                      }
                    >
                      Convert lead
                      <Icon name="arrow" size={16} />
                    </button>
                  </section>
                )}
              {id &&
                !locked &&
                section === "deals" &&
                initial.status === "open" && (
                  <section className="context-action">
                    <h3>Close this opportunity</h3>
                    <p>Keep your forecast accurate with a final outcome.</p>
                    <div className="row-actions">
                      <button
                        type="button"
                        className="button secondary"
                        disabled={busy}
                        onClick={() => void action(`/deals/${id}/won`)}
                      >
                        <Icon name="check" size={16} />
                        Mark won
                      </button>
                      <button
                        type="button"
                        className="button subtle"
                        onClick={() => setLosing(true)}
                      >
                        Mark lost
                      </button>
                    </div>
                    {losing && (
                      <div className="lost-form">
                        <label>
                          What happened?
                          <input
                            required
                            value={reason}
                            onChange={(event) => setReason(event.target.value)}
                            placeholder="Reason for loss"
                          />
                        </label>
                        <button
                          type="button"
                          className="button secondary"
                          disabled={!reason.trim() || busy}
                          onClick={() =>
                            void action(`/deals/${id}/lost`, { reason })
                          }
                        >
                          Confirm lost
                        </button>
                      </div>
                    )}
                  </section>
                )}
              {id && !locked && section === "automations" && (
                <button
                  type="button"
                  className="button secondary"
                  onClick={() =>
                    void action(
                      `/automations/${id}`,
                      { enabled: !initial.enabled },
                      "PATCH",
                    )
                  }
                >
                  {initial.enabled ? "Pause automation" : "Enable automation"}
                </button>
              )}
              {id &&
                !locked &&
                section === "communications" &&
                initial.status !== "sent" && (
                  <section className="context-action">
                    <h3>Saved as a draft</h3>
                    <p>
                      Gmail connection and email sending are not enabled in this
                      release. This draft has not been sent.
                    </p>
                  </section>
                )}
            </div>
            <footer className="drawer-footer">
              {id && !locked && section !== "automations" && (
                <button
                  type="button"
                  className="button delete-button"
                  disabled={busy}
                  onClick={() => {
                    if (
                      window.confirm(
                        "Delete this record? This cannot be undone.",
                      )
                    )
                      void action(
                        `/${entityFor(section)}/${id}`,
                        undefined,
                        "DELETE",
                      );
                  }}
                >
                  Delete
                </button>
              )}
              <button type="button" className="button subtle" onClick={onClose}>
                Cancel
              </button>
              {!locked && (
                <button
                  type="submit"
                  className="button primary"
                  disabled={busy}
                >
                  {busy
                    ? "Saving…"
                    : id
                      ? "Save changes"
                      : `Create ${singular[section] ?? "record"}`}
                </button>
              )}
            </footer>
          </form>
        )}
      </aside>
    </div>
  );
}
function Reports({
  data,
  stages,
  deals,
}: {
  data: Record<string, unknown>;
  stages: Stage[];
  deals: Row[];
}) {
  const router = useRouter();
  const metrics = (data.metrics ?? data) as Record<string, unknown>;
  const source = (data.lead_sources ?? data.sources ?? []) as Row[];
  return (
    <>
      <div className="reports-intro">
        <Icon name="reports" size={27} />
        <div>
          <h2>The complete picture, from your records.</h2>
          <p>
            Live sales and activity totals for your workspace. Export individual
            record lists for deeper analysis.
          </p>
        </div>
      </div>
      <div className="report-grid">
        {Object.entries(metrics)
          .filter(
            ([key, value]) =>
              !["period", "period_basis"].includes(key) &&
              (typeof value === "number" || typeof value === "string"),
          )
          .map(([key, value]) => (
            <div className="report-stat" key={key}>
              <span>{label(key)}</span>
              <strong>
                {/value|revenue|amount|weighted_pipeline/.test(key)
                  ? amount(value)
                  : key === "win_rate" ? `${text(value)}%` : text(value)}
              </strong>
            </div>
          ))}
      </div>
      {source.length > 0 && (
        <section className="panel">
          <div className="panel-heading">
            <h2>Where your leads come from</h2>
          </div>
          <div className="source-list">
            {source.map((item, index) => (
              <div key={item.id ?? index}>
                <span>{text(item.source ?? item.name)}</span>
                <strong>{text(item.count)}</strong>
              </div>
            ))}
          </div>
        </section>
      )}
      <section className="panel">
        <div className="panel-heading">
          <h2>Recent deals</h2>
          <Link href="/deals" className="text-link">
            Explore deals
            <Icon name="arrow" size={16} />
          </Link>
        </div>
        {deals.length ? (
          <DataTable
            rows={deals}
            columns={["name", "amount", "stage_id", "status"]}
            stages={stages}
            onSelect={(row) => {
              router.push(`/deals?id=${row.id}`);
            }}
          />
        ) : (
          <p className="quiet-empty">Create deals to see outcomes here.</p>
        )}
      </section>
    </>
  );
}
function Settings({
  user,
  integrations,
  onUser,
  notify,
}: {
  user: User;
  integrations: Row[];
  onUser: (user: User) => void;
  notify: (message: string) => void;
}) {
  const [tab, setTab] = useState("profile");
  const [team, setTeam] = useState<(User & { is_active?: boolean })[]>([]);
  const [securityRevision, setSecurityRevision] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const loadTeam = useCallback(() => {
    api<User[]>("/team")
      .then(setTeam)
      .catch((failure) => setError((failure as Error).message));
  }, []);
  useEffect(() => {
    if (tab === "team") loadTeam();
  }, [tab, loadTeam]);
  async function submit(
    event: FormEvent<HTMLFormElement>,
    endpoint: string,
    method: string,
  ) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = event.currentTarget;
    const body = Object.fromEntries(new FormData(form));
    try {
      const result = await api<User>(endpoint, {
        method,
        body: JSON.stringify(body),
      });
      if (endpoint === "/me") onUser(result);
      else form.reset();
      if (endpoint === "/team") loadTeam();
      if (endpoint === "/auth/change-password")
        setSecurityRevision((value) => value + 1);
      notify("Settings saved");
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function updateMember(
    member: User & { is_active?: boolean },
    patch: { role?: string; is_active?: boolean },
  ) {
    if (
      patch.is_active === false &&
      !window.confirm(
        `Deactivate ${member.name}? Their active sessions will be revoked.`,
      )
    )
      return;
    setBusy(true);
    setError("");
    try {
      await api(`/team/${member.id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      loadTeam();
      notify("Team member updated");
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="settings-layout">
      <nav className="settings-nav" aria-label="Settings sections">
        {["profile", "team", "integrations", "security"].map((value) => (
          <button
            key={value}
            onClick={() => {
              setTab(value);
              setError("");
            }}
            className={tab === value ? "active" : ""}
          >
            {label(value)}
          </button>
        ))}
      </nav>
      <section className="settings-panel">
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        {tab === "profile" && (
          <>
            <h2>Your profile</h2>
            <p className="muted">
              The details your team sees around the workspace.
            </p>
            <form onSubmit={(event) => void submit(event, "/me", "PATCH")}>
              <label>
                Full name
                <input name="name" defaultValue={user.name} required />
              </label>
              <label>
                Work email
                <input value={user.email} readOnly />
              </label>
              <label>
                Company
                <input value={user.company_name} readOnly />
              </label>
              <div className="settings-save">
                <button className="button primary" disabled={busy}>
                  Save profile
                </button>
              </div>
            </form>
          </>
        )}
        {tab === "security" && (
          <>
            <h2>Change your password</h2>
            <p className="muted">
              Updating your password signs out other sessions.
            </p>
            <form
              onSubmit={(event) =>
                void submit(event, "/auth/change-password", "POST")
              }
            >
              <label>
                Current password
                <input
                  name="current_password"
                  type="password"
                  autoComplete="current-password"
                  required
                />
              </label>
              <label>
                New password
                <input
                  name="new_password"
                  type="password"
                  minLength={8}
                  autoComplete="new-password"
                  required
                />
              </label>
              <div className="settings-save">
                <button className="button primary" disabled={busy}>
                  Update password
                </button>
              </div>
            </form>
            <ActiveSessions key={securityRevision} />
          </>
        )}
        {tab === "team" && (
          <>
            <h2>Your team</h2>
            <p className="muted">
              Give the right people access to this workspace.
            </p>
            {["Owner", "Admin"].includes(user.role) && <TeamInvitations />}
            <div className="team-list">
              {team.map((member) => (
                <div key={member.id}>
                  <span className="record-monogram">
                    {initials(member.name)}
                  </span>
                  <div>
                    <strong>{member.name}</strong>
                    <small>{member.email}</small>
                  </div>
                  <Badge
                    value={
                      member.is_active === false ? "Inactive" : member.role
                    }
                  />
                  {["Owner", "Admin"].includes(user.role) &&
                    member.id !== user.id &&
                    member.role !== "Owner" && (
                      <div className="team-access-controls">
                        <Select
                          aria-label={`Role for ${member.name}`}
                          value={member.role}
                          disabled={busy}
                          onChange={(event) =>
                            void updateMember(member, {
                              role: event.target.value,
                            })
                          }
                        >
                          {[
                            "Admin",
                            "Sales Manager",
                            "Sales Rep",
                            "Support Agent",
                            "Read-only",
                          ].map((role) => (
                            <option key={role}>{role}</option>
                          ))}
                        </Select>
                        <button
                          className="button subtle"
                          disabled={busy}
                          onClick={() =>
                            void updateMember(member, {
                              is_active: member.is_active === false,
                            })
                          }
                        >
                          {member.is_active === false
                            ? "Reactivate"
                            : "Deactivate"}
                        </button>
                      </div>
                    )}
                </div>
              ))}
            </div>
            {["Owner", "Admin", "owner", "admin"].includes(user.role) && (
              <form
                className="team-form"
                onSubmit={(event) => void submit(event, "/team", "POST")}
              >
                <h3>Add a team member</h3>
                <p className="muted">
                  Create a login and share its temporary password securely. No
                  invitation email is sent.
                </p>
                <div className="form-grid">
                  <label>
                    Full name
                    <input name="name" required />
                  </label>
                  <label>
                    Email
                    <input name="email" type="email" required />
                  </label>
                  <label>
                    Temporary password
                    <input
                      name="password"
                      type="password"
                      minLength={8}
                      autoComplete="new-password"
                      required
                    />
                  </label>
                  <label>
                    Role
                    <Select name="role" defaultValue="Sales Rep">
                      {[
                        "Admin",
                        "Sales Manager",
                        "Sales Rep",
                        "Support Agent",
                        "Read-only",
                      ].map((role) => (
                        <option key={role}>{role}</option>
                      ))}
                    </Select>
                  </label>
                </div>
                <div className="settings-save">
                  <button className="button primary" disabled={busy}>
                    Create team member
                  </button>
                </div>
              </form>
            )}
          </>
        )}
        {tab === "integrations" && (
          <>
            <h2>Connected tools</h2>
            <p className="muted">
              Connections are only active when a real provider is configured.
            </p>
            <div className="integration-list">
              {integrations.map((integration, index) => (
                <div key={integration.id ?? index}>
                  <div>
                    <strong>
                      {text(integration.name ?? integration.provider)}
                    </strong>
                    <p>
                      {text(integration.description ?? integration.message) ||
                        "Provider credentials are managed in deployment settings."}
                    </p>
                  </div>
                  <Badge value={integration.status ?? "Not connected"} />
                </div>
              ))}
              {!integrations.length && (
                <p className="quiet-empty">
                  No providers configured. Email can be saved as drafts; Gmail
                  connection is planned for later.
                </p>
              )}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
function GlobalSearch({ onClose }: { onClose: () => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Row[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  useDialogKeyboard(dialogRef, onClose);
  useEffect(() => {
    input.current?.focus();
  }, []);
  useEffect(() => {
    if (!query.trim()) return;
    let current = true;
    const timer = window.setTimeout(() => {
      api<List>(`/search?q=${encodeURIComponent(query)}`)
        .then((data) => {
          if (!current) return;
          setResults(data.items);
          setError("");
        })
        .catch((failure) => { if (current) setError((failure as Error).message); })
        .finally(() => { if (current) setLoading(false); });
    }, 250);
    return () => { current = false; window.clearTimeout(timer); };
  }, [query]);
  return (
    <div className="search-overlay">
      <button
        className="drawer-scrim"
        aria-label="Close search"
        onClick={onClose}
      />
      <div
        ref={dialogRef}
        className="search-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Search workspace"
      >
        <div className="search-input">
          <Icon name="search" />
          <input
            ref={input}
            aria-label="Search workspace"
            placeholder="Search people, companies, deals…"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setLoading(Boolean(event.target.value.trim()));
              setResults([]);
              setError("");
            }}
          />
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Close search"
          >
            <Icon name="close" />
          </button>
        </div>
        <div className="search-results">
          {error && <p role="alert">{error}</p>}
          {loading ? (
            <p>Searching…</p>
          ) : results.length ? (
            results.map((row) => (
              <Link
                key={`${row.entity_type}-${row.id}`}
                href={`/${row.entity_type === "parties" ? "accounts" : text(row.entity_type)}?id=${encodeURIComponent(row.id)}`}
                onClick={onClose}
              >
                <span className="record-monogram">
                  {initials(text(row.name))}
                </span>
                <span>
                  <strong>{text(row.name)}</strong>
                  <small>
                    {text(row.description) || text(row.entity_type)}
                  </small>
                </span>
                <Badge value={row.entity_type} />
              </Link>
            ))
          ) : (
            <p>
              {query
                ? "No matching records. Try a different name."
                : "Search across your entire workspace."}
            </p>
          )}
        </div>
        <div className="search-footer">
          Search is limited to records in your workspace.
        </div>
      </div>
    </div>
  );
}
function ImportExport({
  entity,
  readonly,
  query,
  status,
  sort,
  pipelineId,
  onImport,
}: {
  entity: string;
  readonly: boolean;
  query: string;
  status: string;
  sort: string;
  pipelineId?: string;
  onImport: () => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState("");
  const [errorCsv, setErrorCsv] = useState("");
  async function upload(file: File) {
    setBusy(true);
    setReport("");
    setErrorCsv("");
    try {
      const result = await api<Record<string, unknown>>(`/${entity}/import`, {
        method: "POST",
        body: JSON.stringify({ csv: await file.text(), mode: "skip" }),
      });
      setErrorCsv(text(result.error_csv));
      setReport(
        `Import complete: ${text(result.created ?? result.imported ?? 0)} created, ${text(result.skipped ?? 0)} skipped, ${Array.isArray(result.errors) ? result.errors.length : text(result.failed ?? 0)} errors.`,
      );
      onImport();
    } catch (failure) {
      setReport((failure as Error).message);
    } finally {
      setBusy(false);
      if (ref.current) ref.current.value = "";
    }
  }
  return (
    <div className="import-export">
      <input
        ref={ref}
        className="sr-only"
        type="file"
        accept=".csv,text/csv"
        aria-label="Import CSV file"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void upload(file);
        }}
      />
      <button
        className="button subtle"
        disabled={readonly || busy}
        onClick={() => ref.current?.click()}
      >
        {busy ? "Importing…" : "Import CSV"}
      </button>
      <a
        className="button subtle"
        href={`/api/v1/${entity}/export?${new URLSearchParams({ q: query, status, sort: sort.split(":")[0] ?? "updated_at", order: sort.split(":")[1] ?? "desc", ...(entity === "deals" && pipelineId ? { pipeline_id: pipelineId } : {}) })}`}
        download
      >
        <Icon name="download" size={16} />
        Export
      </a>
      <details className="data-help">
        <summary>CSV help</summary>
        <p>Import a UTF-8 CSV with a name header and up to 10,000 rows. Existing email, phone or name matches are skipped. Invalid rows appear in a downloadable error report. Excel workbooks must first be saved as CSV. Exports include all matching records across all pages, using the current search, status and sort.{entity === "deals" && pipelineId ? " Deal exports are limited to the selected pipeline." : ""}</p>
      </details>
      {report && (
        <div className="import-report" role="status">
          <div>
            {report}
            {errorCsv && (
              <button
                className="text-link"
                onClick={() =>
                  downloadCsv(errorCsv, `${entity}-import-errors.csv`)
                }
              >
                Download error report
              </button>
            )}
          </div>
          <button
            className="icon-button"
            aria-label="Dismiss import result"
            onClick={() => setReport("")}
          >
            <Icon name="close" size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
function SampleData({ onLoaded }: { onLoaded: () => void }) {
  const [seeded, setSeeded] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    api<{ seeded: boolean }>("/demo/status")
      .then((result) => setSeeded(result.seeded))
      .catch((failure) => setError((failure as Error).message));
  }, []);
  async function seed() {
    setBusy(true);
    try {
      await api("/demo/seed", { method: "POST", body: "{}" });
      setSeeded(true);
      onLoaded();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (seeded === null && !error) return null;
  return seeded ? (
    <div className="sample-banner loaded">
      <span>Sample workspace · fictional business records</span>
    </div>
  ) : (
    <div className="sample-banner">
      <div>
        <strong>Take a look around with sample data.</strong>
        <span>
          Optional, clearly labelled fictional leads, deals, and tasks — saved
          to your workspace.
        </span>
        {error && <p role="alert">{error}</p>}
      </div>
      <button
        className="button secondary"
        disabled={busy}
        onClick={() => void seed()}
      >
        {busy ? "Loading…" : "Load sample workspace"}
      </button>
    </div>
  );
}
function Notifications() {
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<Row[]>([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = useCallback(() => {
    setLoading(true);
    setError("");
    api<List & { unread: number }>("/notifications")
      .then((result) => {
        setRows(result.items);
        setUnread(result.unread);
      })
      .catch((failure) => setError((failure as Error).message))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(load, 0);
    return () => window.clearTimeout(timer);
  }, [load]);
  useEffect(() => {
    if (!open) return;
    const dismissOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !containerRef.current?.contains(event.target)) setOpen(false);
    };
    const dismissEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") { setOpen(false); triggerRef.current?.focus(); }
    };
    document.addEventListener("pointerdown", dismissOutside);
    document.addEventListener("keydown", dismissEscape);
    return () => {
      document.removeEventListener("pointerdown", dismissOutside);
      document.removeEventListener("keydown", dismissEscape);
    };
  }, [open]);
  async function read(row: Row) {
    try {
      await api(`/notifications/${row.id}/read`, {
        method: "POST",
        body: "{}",
      });
      load();
    } catch (failure) {
      setError((failure as Error).message);
    }
  }
  return (
    <div className="notifications" ref={containerRef}>
      <button
        ref={triggerRef}
        className="icon-button"
        aria-label="Notifications"
        aria-expanded={open}
        onClick={() => { if (!open) load(); setOpen(!open); }}
      >
        <svg
          width="19"
          height="19"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          aria-hidden="true"
        >
          <path
            d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {unread > 0 && <span className="notification-dot" />}
      </button>
      {open && (
        <div className="notification-panel">
          <div className="notification-heading">
            <h3>Notifications</h3>
            <span>{unread} unread</span>
          </div>
          {error && <p role="alert">{error} <button onClick={load}>Try again</button></p>}
          {loading ? <p role="status">Loading notifications…</p> : error ? null : rows.length ? (
            rows.slice(0, 12).map((row) => (
              <button key={row.id} onClick={() => void read(row)}>
                <strong>{text(row.title ?? row.message)}</strong>
                <span>{row.body ? text(row.body).slice(0, 120) : formatTimestamp(row.created_at)}</span>
                {!row.read && <small>Mark as read</small>}
              </button>
            ))
          ) : (
            <p>You’re all caught up.</p>
          )}
        </div>
      )}
    </div>
  );
}
function TicketConversation({
  ticketId,
  readonly,
}: {
  ticketId: string;
  readonly: boolean;
}) {
  const [rows, setRows] = useState<Row[]>([]);
  const [body, setBody] = useState("");
  const [internal, setInternal] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const requestKey = useRef<{ fingerprint: string; key: string } | null>(null);
  const load = useCallback(() => {
    api<List>(`/tickets/${ticketId}/messages`)
      .then((result) => setRows(result.items))
      .catch((failure) => setError((failure as Error).message));
  }, [ticketId]);
  useEffect(() => {
    load();
  }, [load]);
  async function add() {
    setBusy(true);
    setError("");
    try {
      const fingerprint = JSON.stringify({ body, internal });
      if (requestKey.current?.fingerprint !== fingerprint)
        requestKey.current = { fingerprint, key: crypto.randomUUID() };
      await api(`/tickets/${ticketId}/messages`, {
        method: "POST",
        body: JSON.stringify({ body, internal }),
        headers: { "Idempotency-Key": requestKey.current.key },
      });
      requestKey.current = null;
      setBody("");
      load();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="context-action">
      <h3>Conversation</h3>
      <p>
        Internal notes stay with your team. Customer replies are saved as drafts
        until delivery is connected.
      </p>
      {rows.map((row) => (
        <article
          className={`ticket-message ${row.internal ? "internal" : ""}`}
          key={row.id}
        >
          <Badge
            value={row.internal ? "Internal note" : "Reply draft · not sent"}
          />
          <p>{text(row.body)}</p>
          <small>{formatTimestamp(row.created_at)}</small>
        </article>
      ))}
      {error && (
        <div role="alert" className="form-error">
          {error}
        </div>
      )}
      <label>
        Message type
        <Select
          disabled={readonly || busy}
          value={internal ? "note" : "reply"}
          onChange={(event) => setInternal(event.target.value === "note")}
        >
          <option value="note">Internal note</option>
          <option value="reply">Customer reply draft</option>
        </Select>
      </label>
      <label className="message-body">
        Message
        <textarea
          rows={3}
          disabled={readonly || busy}
          value={body}
          onChange={(event) => setBody(event.target.value)}
          placeholder={
            internal ? "Share context with your team…" : "Write a reply draft…"
          }
        />
      </label>
      <button
        className="button secondary"
        type="button"
        onClick={() => void add()}
        disabled={readonly || busy || !body.trim()}
      >
        {busy ? "Saving…" : internal ? "Add internal note" : "Save reply draft"}
      </button>
    </section>
  );
}
function EmailTemplates({ readonly }: { readonly: boolean }) {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const requestKey = useRef<{ fingerprint: string; key: string } | null>(null);
  const load = useCallback(() => {
    api<List>("/email/templates")
      .then((result) => setRows(result.items))
      .catch((failure) => setError((failure as Error).message));
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = event.currentTarget;
    try {
      const payload = Object.fromEntries(new FormData(form));
      requestKey.current = idempotencyRequest(payload, requestKey.current);
      await api("/email/templates", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: { "Idempotency-Key": requestKey.current.key },
      });
      requestKey.current = null;
      form.reset();
      load();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function remove(id: string) {
    try {
      await api(`/email/templates/${id}`, { method: "DELETE" });
      load();
    } catch (failure) {
      setError((failure as Error).message);
    }
  }
  return (
    <section className="utility-panel">
      <button
        className="utility-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <Icon name="mail" size={17} />
        <span>Reusable email templates</span>
        <span>{rows.length} templates</span>
        <Icon name="down" size={16} />
      </button>
      {open && (
        <div className="utility-body">
          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}
          {rows.map((row) => (
            <article className="email-template" key={row.id}>
              <div>
                <h3>{text(row.name)}</h3>
                <strong>{text(row.subject)}</strong>
                <p>{text(row.body)}</p>
              </div>
              <button
                className="button subtle"
                disabled={readonly}
                onClick={() => {
                  if (window.confirm("Delete this template?"))
                    void remove(row.id);
                }}
              >
                Delete
              </button>
            </article>
          ))}
          <form onSubmit={(event) => void add(event)}>
            <h3>Create a template</h3>
            <div className="form-grid">
              <label>
                Name
                <input name="name" required />
              </label>
              <label>
                Subject
                <input name="subject" required />
              </label>
              <label className="full-width">
                Message
                <textarea
                  rows={3}
                  name="body"
                  required
                  placeholder="Hi {{name}},"
                />
              </label>
            </div>
            <button className="button secondary" disabled={readonly || busy}>
              {busy ? "Saving…" : "Save template"}
            </button>
          </form>
        </div>
      )}
    </section>
  );
}
function AutomationRuns() {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    if (open)
      api<List>("/automations/runs")
        .then((result) => setRows(result.items))
        .catch((failure) => setError((failure as Error).message));
  }, [open]);
  return (
    <section className="utility-panel">
      <button
        className="utility-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <Icon name="clock" size={17} />
        <span>Automation execution log</span>
        <Icon name="down" size={16} />
      </button>
      {open && (
        <div className="utility-body">
          {error && <p role="alert">{error}</p>}
          {rows.length ? (
            rows.map((row) => (
              <div className="automation-run" key={row.id}>
                <span>
                  {text(row.rule_name ?? row.trigger ?? row.automation_id)}
                </span>
                <Badge value={row.status} />
                <span>
                  {formatTimestamp(row.created_at)}
                </span>
              </div>
            ))
          ) : (
            <p className="muted">
              No automations have run yet. New matching records will trigger
              enabled rules.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
function RelationSelect({
  entity,
  value,
  onChange,
}: {
  entity: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const [rows, setRows] = useState<Row[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (!entity) return;
    let active = true;
    const timer = window.setTimeout(() => {
      api<List>(`/${entity}?limit=50&q=${encodeURIComponent(query)}`)
        .then(async (result) => {
          const items = result.items;
          if (value && !items.some((row) => row.id === value)) {
            const selected = await api<Row>(`/${entity}/${value}`);
            items.unshift(selected);
          }
          if (active) {
            setRows(items);
            setError("");
          }
        })
        .catch((failure) => { if (active) setError((failure as Error).message); });
    }, 180);
    return () => { active = false; window.clearTimeout(timer); };
  }, [entity, value, query]);
  return (
    <span className="relation-field">
      <input
        aria-label={`Search ${entity || "related records"}`}
        placeholder={entity ? "Search by name…" : "Choose a record type first"}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        disabled={!entity}
      />
      <Select
        aria-label={`Select ${entity || "related record"}`}
        value={value}
        disabled={!entity}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">None</option>
        {rows.map((row) => (
          <option key={row.id} value={row.id}>
            {text(row.name)}
          </option>
        ))}
      </Select>
      {value && entity && (
        <Link
          className="text-link related-link"
          href={`/${entity === "parties" ? "accounts" : entity}?id=${encodeURIComponent(value)}`}
        >
          Open linked record
          <Icon name="arrow" size={12} />
        </Link>
      )}
      {error && (
        <span className="field-error" role="alert">
          {error}
        </span>
      )}
    </span>
  );
}
function useDialogKeyboard(
  dialogRef: RefObject<HTMLElement | null>,
  onClose: () => void,
) {
  const closeRef = useRef(onClose);
  useEffect(() => {
    closeRef.current = onClose;
  }, [onClose]);
  useEffect(() => {
    const previouslyFocused =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const keydown = (event: KeyboardEvent) => {
      const dialogs = document.querySelectorAll<HTMLElement>('[role="dialog"]');
      const dialog = dialogRef.current;
      if (!dialog || dialogs.item(dialogs.length - 1) !== dialog) return;
      if (event.key === "Escape") {
        event.preventDefault();
        closeRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const controls = dialog
        ? Array.from(
            dialog.querySelectorAll<HTMLElement>(
              'a[href],button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled]),[tabindex="0"]',
            ),
          ).filter((element) => element.getClientRects().length > 0 && !element.matches(":disabled") && element.tabIndex >= 0)
        : [];
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (!first || !last) return;
      if (
        event.shiftKey &&
        (document.activeElement === first ||
          !dialog?.contains(document.activeElement))
      ) {
        event.preventDefault();
        last.focus();
      } else if (
        !event.shiftKey &&
        (document.activeElement === last ||
          !dialog?.contains(document.activeElement))
      ) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("keydown", keydown);
      if (previouslyFocused && document.contains(previouslyFocused))
        previouslyFocused.focus();
    };
  }, [dialogRef]);
}
function downloadCsv(csv: string, filename: string) {
  const url = URL.createObjectURL(
    new Blob([csv], { type: "text/csv;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function Attachments({
  entity,
  recordId,
  readonly,
}: {
  entity: string;
  recordId: string;
  readonly: boolean;
}) {
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [retryFile, setRetryFile] = useState<File | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const requestSequence = useRef(0);
  const uploadRequest = useRef<{ fingerprint: string; key: string } | null>(null);
  const scope = new URLSearchParams({
    entity_type: entity,
    entity_id: recordId,
  }).toString();
  const load = useCallback(async () => {
    const sequence = ++requestSequence.current;
    setLoading(true);
    setLoadError("");
    try {
      const result = await api<List>(`/attachments?${scope}`);
      if (sequence === requestSequence.current) setRows(result.items);
    } catch (failure) {
      if (sequence === requestSequence.current) setLoadError((failure as Error).message);
    } finally {
      if (sequence === requestSequence.current) setLoading(false);
    }
  }, [scope]);
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => { window.clearTimeout(timer); requestSequence.current += 1; };
  }, [load]);
  async function upload(file: File) {
    setError("");
    setRetryFile(null);
    if (file.size > 10 * 1024 * 1024) {
      setError("Choose a file smaller than 10 MB.");
      if (input.current) input.current.value = "";
      return;
    }
    setBusy(true);
    try {
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", await file.arrayBuffer())))
        .map(byte => byte.toString(16).padStart(2, "0")).join("");
      const fingerprint = JSON.stringify([scope, file.name, file.type, digest]);
      if (uploadRequest.current?.fingerprint !== fingerprint)
        uploadRequest.current = { fingerprint, key: crypto.randomUUID() };
      const response = await fetch(
        `/api/v1/attachments?${scope}&filename=${encodeURIComponent(file.name)}`,
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": file.type || "application/octet-stream",
            "Idempotency-Key": uploadRequest.current.key,
          },
          body: file,
        },
      );
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        if (response.status === 401) window.dispatchEvent(new Event("relay:session-expired"));
        throw new Error(
          payload?.error?.message ?? "The attachment could not be uploaded. Please try again.",
        );
      }
      uploadRequest.current = null;
      await load();
    } catch (failure) {
      setError((failure as Error).message);
      setRetryFile(file);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }
  async function remove(id: string) {
    setBusy(true);
    setError("");
    try {
      await api(`/attachments/${id}`, { method: "DELETE" });
      await load();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="context-action">
      <h3>Attachments</h3>
      <p>
        Keep useful documents with this record. PDF, images, text, or CSV; up to
        10 MB each.
      </p>
      {error && (
        <div role="alert" className="form-error">
          {error}
          {retryFile && !readonly && <button type="button" className="text-link" disabled={busy}
            onClick={() => void upload(retryFile)}>Retry upload</button>}
        </div>
      )}
      {loadError && <div role="alert" className="form-error">{loadError}
        <button type="button" className="text-link" disabled={loading} onClick={() => void load()}>Retry attachments</button>
      </div>}
      {loading ? <p role="status">Loading attachments…</p> : !loadError && rows.length === 0 ? <p className="muted">No attachments yet.</p> : null}
      {!loading && !loadError && <div className="attachment-list">
        {rows.map((row) => (
          <div key={row.id}>
            <a href={`/api/v1/attachments/${row.id}/download`} download>
              <Icon name="download" size={16} />
              <span>
                {text(row.filename)}
                <small>{(Number(row.size_bytes) / 1024).toFixed(1)} KB</small>
              </span>
            </a>
            {!readonly && (
              <button
                type="button"
                className="icon-button"
                aria-label={`Delete ${text(row.filename)}`}
                disabled={busy}
                onClick={() => {
                  if (window.confirm("Delete this attachment?"))
                    void remove(row.id);
                }}
              >
                <Icon name="close" size={15} />
              </button>
            )}
          </div>
        ))}
      </div>}
      {!readonly && (
        <>
          <input
            ref={input}
            className="sr-only"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.txt,.csv"
            aria-label="Choose attachment"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void upload(file);
            }}
          />
          <button
            type="button"
            className="button secondary"
            onClick={() => input.current?.click()}
            disabled={busy}
          >
            <Icon name="plus" size={15} />
            {busy ? "Uploading…" : "Add attachment"}
          </button>
        </>
      )}
    </section>
  );
}
function LeadDuplicates({
  id,
  email,
  phone,
  version,
  onMerged,
}: {
  id: string;
  email: string;
  phone: string;
  version?: number;
  onMerged: () => void;
}) {
  const [matches, setMatches] = useState<Row[]>([]);
  const [error, setError] = useState("");
  const [target, setTarget] = useState("");
  const [showMerge, setShowMerge] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (!email.trim() && !phone.trim()) {
        setMatches([]);
        return;
      }
      const stripped = phone.replace(/[\s()\-]/g, "");
      const normalized = /^\d{10}$/.test(stripped)
        ? `+91${stripped}`
        : stripped;
      api<List>(
        `/leads/duplicates?${new URLSearchParams({ email, phone: normalized })}`,
      )
        .then((result) => {
          setMatches(result.items.filter((row) => row.id !== id));
          setError("");
        })
        .catch((failure) => setError((failure as Error).message));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [email, phone, id]);
  async function merge() {
    if (!target || target === id) {
      setError("Choose a different lead to keep.");
      return;
    }
    if (
      !window.confirm(
        "Merge this lead into the selected lead? This record will be archived. Its notes, history, and activities will be preserved.",
      )
    )
      return;
    setBusy(true);
    setError("");
    try {
      await api(`/leads/${id}/merge`, {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ target_id: target, source_version: version }),
      });
      onMerged();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      {matches.length > 0 && (
        <section className="duplicate-warning">
          <h3>Possible duplicate {matches.length === 1 ? "lead" : "leads"}</h3>
          <p>These records share an email address or phone number.</p>
          {matches.map((row) => (
            <div key={row.id}>
              <Link href={`/leads?id=${row.id}`}>
                {text(row.name)}
                <Icon name="arrow" size={13} />
              </Link>
              {id && (
                <button
                  type="button"
                  className="text-link"
                  onClick={() => {
                    setTarget(row.id);
                    setShowMerge(true);
                  }}
                >
                  Merge into this lead
                </button>
              )}
            </div>
          ))}
        </section>
      )}
      {id && (
        <section className="context-action">
          <button
            type="button"
            className="text-link"
            onClick={() => setShowMerge(!showMerge)}
          >
            {showMerge ? "Close merge options" : "Merge with another lead"}
          </button>
          {showMerge && (
            <div className="merge-options">
              <p>
                The selected lead is kept. This record is archived and its
                notes, tags, activities, and history are preserved.
              </p>
              <label>
                Lead to keep
                <RelationSelect
                  entity="leads"
                  value={target}
                  onChange={setTarget}
                />
              </label>
              <button
                type="button"
                className="button secondary"
                disabled={!target || target === id || busy}
                onClick={() => void merge()}
              >
                {busy ? "Merging…" : "Merge lead"}
              </button>
            </div>
          )}
        </section>
      )}
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
    </>
  );
}
