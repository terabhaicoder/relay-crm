import type { UserResponse } from "./schema";
export type Row = { id: string; [key: string]: unknown };
export type User = UserResponse;
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const fields = payload?.error?.details?.fields;
    const invalidFields = Array.isArray(fields)
      ? fields
          .map((entry: { field?: string }) =>
            entry.field?.replace(/^body\./, "").replaceAll("_", " "),
          )
          .filter(Boolean)
      : [];
    const message = invalidFields.length
      ? `Please check: ${invalidFields.join(", ")}.`
      : (payload?.error?.message ??
        `Request failed (${response.status}). Please try again.`);
    if (response.status === 401 && !path.startsWith("/auth/"))
      window.dispatchEvent(new Event("relay:session-expired"));
    throw new ApiError(
      message,
      response.status,
      payload?.error?.code ?? "REQUEST_FAILED",
    );
  }
  return payload as T;
}
export function text(value: unknown): string {
  return value == null ? "" : String(value);
}
export function submittedDate(day: string, existing: unknown): string | null {
  if (!day) return null;
  const original = text(existing);
  // Date controls only display a day. An unrelated edit must not discard a
  // stored appointment time that the user could not see or change here.
  return day === original.slice(0, 10) ? original : day;
}
export function idempotencyRequest(
  body: Record<string, unknown>,
  previous: { fingerprint: string; key: string } | null,
): { fingerprint: string; key: string } {
  const fingerprint = JSON.stringify(body);
  return previous?.fingerprint === fingerprint
    ? previous : { fingerprint, key: crypto.randomUUID() };
}
/** Stored timestamps are UTC; this release displays Asia/Kolkata explicitly.
 * Date-only business values are kept unchanged, without timezone conversion.
 */
export function formatTimestamp(value: unknown): string {
  const raw = text(value).trim();
  if (!raw) return "—";
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  const normalized = raw.replace(" ", "T");
  const utc = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(normalized) ? normalized : `${normalized}Z`;
  const date = new Date(utc);
  if (Number.isNaN(date.getTime())) return raw;
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata", day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZoneName: "short",
  }).format(date);
}
export function amount(value: unknown): string {
  const number = Number(value ?? 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(number) ? number : 0);
}
