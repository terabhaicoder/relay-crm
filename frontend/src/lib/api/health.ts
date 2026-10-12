import type { ReadinessResponse } from "./schema";

type Readiness = { message: string };

export async function getReadiness(): Promise<Readiness> {
  try {
    const origin = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(`${origin}/api/v1/health/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return { message: "Backend is reachable but not ready. Check database and queue services." };
    const payload: unknown = await response.json();
    if (typeof payload !== "object" || payload === null || !("status" in payload) || payload.status !== "ok") {
      return { message: "Backend returned an unexpected response. Review the service configuration." };
    }
    const readiness: ReadinessResponse = payload as ReadinessResponse;
    return { message: readiness.status === "ok" ? "Backend and database are ready." : "Backend returned an unexpected response. Review the service configuration." };
  } catch {
    // A transport failure remains explicitly unavailable; do not display connection details.
    return { message: "Backend is unavailable. Start the backend and its required services, then refresh this page." };
  }
}
