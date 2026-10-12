"use client";

import { Select } from "@/components/ui/select";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, ApiError, formatTimestamp, User } from "@/lib/api/client";
import { Icon } from "./icon";

type Invitation = { email: string; role: string; company_name: string };
type InviteResult = {
  token: string;
  email: string;
  role: string;
  expires_at: string;
  delivery: string;
};
type Session = {
  id: string;
  created_at: string;
  expires_at: string;
  current: boolean;
};
const roles = [
  "Admin",
  "Sales Manager",
  "Sales Rep",
  "Support Agent",
  "Read-only",
];

export function InvitationAcceptance() {
  const token = useSearchParams().get("token") ?? "";
  return <InvitationForm key={token} token={token} />;
}

function InvitationForm({ token }: { token: string }) {
  const router = useRouter();
  const [details, setDetails] = useState<Invitation | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    Promise.all([
      token
        ? api<Invitation>(`/auth/invites/${encodeURIComponent(token)}`)
        : Promise.reject(
            new Error(
              "This invitation link is incomplete. Ask your workspace administrator for a new link.",
            ),
          ),
      api<User>("/auth/me").catch((failure) => {
        if (failure instanceof ApiError && failure.status === 401) return null;
        throw failure;
      }),
    ])
      .then(([invitation, user]) => {
        if (!cancelled) {
          setDetails(invitation);
          setCurrentUser(user);
        }
      })
      .catch((failure) => {
        if (!cancelled)
          setError(
            failure instanceof ApiError && failure.status === 404
              ? "This invitation has expired or has already been used. Ask your workspace administrator for a new link."
              : (failure as Error).message,
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);
  async function logout() {
    setBusy(true);
    try {
      await api("/auth/logout", { method: "POST", body: "{}" });
      setCurrentUser(null);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function accept(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api<User>("/auth/accept-invite", {
        method: "POST",
        body: JSON.stringify({
          ...Object.fromEntries(new FormData(event.currentTarget)),
          token,
        }),
      });
      router.replace("/dashboard");
      router.refresh();
    } catch (failure) {
      setError((failure as Error).message);
      setBusy(false);
    }
  }
  return (
    <main className="invite-page">
      <div className="invite-shell">
        <Link className="invite-brand" href="/">
          relay.
        </Link>
        {loading ? (
          <p role="status">Checking your invitation…</p>
        ) : (
          <>
            <h1>
              {details
                ? `Join ${details.company_name}`
                : "Invitation unavailable"}
            </h1>
            {error && (
              <div className="form-error" role="alert">
                {error}
              </div>
            )}
            {details && (
              <>
                <p className="muted">
                  You have been invited as {details.role}. Create your own
                  password to join this workspace.
                </p>
                {currentUser ? (
                  <div className="context-action">
                    <p>
                      You are currently signed in as {currentUser.email}. Sign
                      out before accepting an invitation for {details.email}.
                    </p>
                    <button
                      className="button primary"
                      disabled={busy}
                      onClick={() => void logout()}
                    >
                      Sign out to continue
                    </button>
                  </div>
                ) : (
                  <form onSubmit={(event) => void accept(event)}>
                    <label>
                      Invited email
                      <input
                        type="email"
                        value={details.email}
                        readOnly
                        autoComplete="email"
                      />
                    </label>
                    <label>
                      Your name
                      <input
                        name="name"
                        required
                        maxLength={200}
                        autoComplete="name"
                      />
                    </label>
                    <label>
                      Create password
                      <input
                        name="password"
                        type="password"
                        required
                        minLength={8}
                        maxLength={128}
                        autoComplete="new-password"
                      />
                    </label>
                    <p className="muted">Use at least 8 characters.</p>
                    <button
                      className="button primary auth-submit"
                      disabled={busy}
                    >
                      {busy ? "Joining…" : "Join workspace"}
                      <Icon name="arrow" size={16} />
                    </button>
                  </form>
                )}
              </>
            )}
            <Link className="text-link" href="/dashboard">
              Return to sign in
            </Link>
          </>
        )}
      </div>
    </main>
  );
}

export function TeamInvitations() {
  const [invitation, setInvitation] = useState<InviteResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setCopied(false);
    const form = event.currentTarget;
    try {
      const result = await api<InviteResult>("/team/invites", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(new FormData(form))),
      });
      setInvitation(result);
      form.reset();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const link =
    invitation && typeof window !== "undefined"
      ? `${window.location.origin}/invite?token=${encodeURIComponent(invitation.token)}`
      : "";
  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
    } catch {
      setError(
        "Copying was unavailable. Select the invitation link and copy it manually.",
      );
    }
  }
  return (
    <section className="context-action">
      <h3>Invite a teammate</h3>
      <p>
        Create a private link so your teammate can set their own password. Share
        it securely; no invitation email is sent.
      </p>
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
      <form onSubmit={(event) => void submit(event)}>
        <div className="form-grid">
          <label>
            Invite email
            <input name="email" type="email" maxLength={254} required />
          </label>
          <label>
            Invitation role
            <Select aria-label="Invitation role" name="role" defaultValue="Sales Rep">
              {roles.map((role) => (
                <option key={role}>{role}</option>
              ))}
            </Select>
          </label>
        </div>
        <button className="button primary settings-save" disabled={busy}>
          {busy ? "Creating link…" : "Create invitation link"}
        </button>
      </form>
      {invitation && (
        <div className="invite-result" role="status">
          <strong>Invitation ready for {invitation.email}</strong>
          <p>
            Expires {formatTimestamp(invitation.expires_at)}. A
            new invitation for this email replaces its previous unused link.
          </p>
          <label>
            Private invitation link
            <input
              value={link}
              readOnly
              onFocus={(event) => event.target.select()}
            />
          </label>
          <button
            type="button"
            className="button secondary"
            onClick={() => void copy()}
          >
            {copied ? "Copied" : "Copy invitation link"}
          </button>
        </div>
      )}
    </section>
  );
}

export function ActiveSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const load = useCallback(() => {
    api<Session[]>("/auth/sessions")
      .then(setSessions)
      .catch((failure) => setError((failure as Error).message))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  async function revoke(id: string) {
    setBusy(true);
    setError("");
    try {
      await api(`/auth/sessions/${id}`, { method: "DELETE" });
      load();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function revokeAll() {
    if (!window.confirm("Sign out of every session, including this one?"))
      return;
    setBusy(true);
    try {
      await api("/auth/logout-all", { method: "POST", body: "{}" });
      window.location.reload();
    } catch (failure) {
      setError((failure as Error).message);
      setBusy(false);
    }
  }
  return (
    <section className="context-action">
      <h3>Active sessions</h3>
      <p>Revoke access on sessions you no longer need.</p>
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
      {loading ? (
        <p role="status">Loading sessions…</p>
      ) : (
        sessions.map((session) => (
          <div className="session-row" key={session.id}>
            <div>
              <strong>
                {session.current ? "This session" : "Other session"}
              </strong>
              <span>
                Signed in {formatTimestamp(session.created_at)}
              </span>
              <small>
                Expires {formatTimestamp(session.expires_at)}
              </small>
            </div>
            {!session.current && (
              <button
                className="button subtle"
                disabled={busy}
                onClick={() => void revoke(session.id)}
              >
                Revoke session
              </button>
            )}
          </div>
        ))
      )}
      <button
        className="button secondary settings-save"
        disabled={busy}
        onClick={() => void revokeAll()}
      >
        Sign out all sessions
      </button>
    </section>
  );
}
