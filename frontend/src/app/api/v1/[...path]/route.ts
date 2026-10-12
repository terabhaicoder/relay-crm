import { NextRequest, NextResponse } from "next/server";
class RequestTooLarge extends Error {}
async function readBody(
  request: NextRequest,
  limit: number,
): Promise<ArrayBuffer | undefined> {
  const declared = Number(request.headers.get("content-length") ?? 0);
  if (declared > limit) throw new RequestTooLarge();
  if (!request.body) return undefined;
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > limit) {
        await reader.cancel();
        throw new RequestTooLarge();
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return bytes.buffer;
}
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const target = `${process.env.BACKEND_URL ?? "http://127.0.0.1:8010"}/api/v1/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;
  try {
    const headers = new Headers();
    for (const name of [
      "content-type",
      "cookie",
      "idempotency-key",
      "origin",
    ]) {
      const value = request.headers.get(name);
      if (value) headers.set(name, value);
    }
    const limit =
      path[0] === "attachments"
        ? 10 * 1024 * 1024
        : path[0] === "auth"
          ? 16 * 1024
          : 12 * 1024 * 1024;
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method)
        ? undefined
        : await readBody(request, limit),
      cache: "no-store",
      signal: AbortSignal.timeout(path.at(-1) === "import" ? 120_000 : 15_000),
      redirect: "manual",
    });
    const result = new NextResponse(
      [204, 205, 304].includes(upstream.status)
        ? null
        : await upstream.arrayBuffer(),
      { status: upstream.status },
    );
    result.headers.set("cache-control", "no-store");
    result.headers.set("x-content-type-options", "nosniff");
    const contentType = upstream.headers.get("content-type");
    if (contentType) result.headers.set("content-type", contentType);
    for (const name of [
      "content-disposition",
      "x-request-id",
      "cache-control",
      "x-content-type-options",
    ]) {
      const value = upstream.headers.get(name);
      if (value) result.headers.set(name, value);
    }
    for (const cookie of upstream.headers.getSetCookie())
      result.headers.append("set-cookie", cookie);
    return result;
  } catch (failure) {
    if (failure instanceof RequestTooLarge)
      return NextResponse.json(
        {
          error: {
            code: "REQUEST_TOO_LARGE",
            message:
              "This request is too large. Attachments must be 10 MB or smaller.",
            details: {},
          },
        },
        {
          status: 413,
          headers: {
            "cache-control": "no-store",
            "x-content-type-options": "nosniff",
          },
        },
      );
    return NextResponse.json(
      {
        error: {
          code: "SERVICE_UNAVAILABLE",
          message: "The CRM service is unavailable. Please try again shortly.",
          details: {},
        },
      },
      { status: 503, headers: { "cache-control": "no-store" } },
    );
  }
}
export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const PUT = proxy;
