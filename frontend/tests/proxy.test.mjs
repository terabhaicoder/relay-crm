import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";
const require = createRequire(import.meta.url);
const { NextRequest } = require("next/server");
const source = readFileSync(new URL("../src/app/api/v1/[...path]/route.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
// These unit tests stub only the upstream HTTP transport; no runtime API is mocked.
function createProxy(fetch) {
  const compiledModule = { exports: {} };
  vm.runInNewContext(compiled, { module: compiledModule, exports: compiledModule.exports, require, fetch, Headers, AbortSignal, Uint8Array, process: { env: { BACKEND_URL: "http://backend.test" } } });
  return compiledModule.exports;
}
const params = (...path) => ({ params: Promise.resolve({ path }) });

test("private downloads preserve binary bytes and security headers", async () => {
  const bytes = new Uint8Array([0, 255, 128, 34, 10]);
  const route = createProxy(async (url, options) => {
    assert.equal(url, "http://backend.test/api/v1/attachments/example/download");
    assert.equal(options.headers.get("cookie"), "erp_session=unit-test-token");
    assert.equal(options.headers.get("x-forwarded-for"), null);
    return new Response(bytes, { headers: { "Content-Type": "application/octet-stream", "Content-Disposition": "attachment; filename=example.bin", "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" } });
  });
  const response = await route.GET(new NextRequest("http://localhost/api/v1/attachments/example/download", { headers: { cookie: "erp_session=unit-test-token", "x-forwarded-for": "spoofed" } }), params("attachments", "example", "download"));
  assert.deepEqual(new Uint8Array(await response.arrayBuffer()), bytes);
  assert.equal(response.headers.get("cache-control"), "private, no-store");
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
  assert.equal(response.headers.get("content-disposition"), "attachment; filename=example.bin");
});

test("logout forwards cookie clearing with an actual empty 204 body", async () => {
  const route = createProxy(async (_url, options) => {
    assert.equal(options.headers.get("origin"), "https://crm.example.test");
    return new Response(null, { status: 204, headers: { "set-cookie": "erp_session=; Path=/; Max-Age=0; HttpOnly" } });
  });
  const response = await route.POST(new NextRequest("http://localhost/api/v1/auth/logout", { method: "POST", headers: { origin: "https://crm.example.test" }, body: "{}" }), params("auth", "logout"));
  assert.equal(response.status, 204);
  assert.equal(await response.text(), "");
  assert.match(response.headers.get("set-cookie"), /Max-Age=0/);
  assert.equal(response.headers.get("cache-control"), "no-store");
});

test("raw attachment uploads reach upstream byte for byte", async () => {
  const bytes = new Uint8Array([0, 128, 255, 65]);
  const route = createProxy(async (_url, options) => { assert.deepEqual(new Uint8Array(options.body), bytes); return Response.json({ id: "file-id" }, { status: 201 }); });
  const response = await route.POST(new NextRequest("http://localhost/api/v1/attachments?filename=test.png", { method: "POST", headers: { "content-type": "image/png" }, body: bytes }), params("attachments"));
  assert.equal(response.status, 201);
});

test("oversized auth body is rejected without an upstream request", async () => {
  let called = false;
  const route = createProxy(async () => { called = true; return Response.json({}); });
  const response = await route.POST(new NextRequest("http://localhost/api/v1/auth/login", { method: "POST", body: "x".repeat(16 * 1024 + 1) }), params("auth", "login"));
  assert.equal(response.status, 413);
  assert.equal(called, false);
});

test("declared oversized attachment is rejected before buffering", async () => {
  let called = false;
  const route = createProxy(async () => { called = true; return Response.json({}); });
  const response = await route.POST(new NextRequest("http://localhost/api/v1/attachments", { method: "POST", headers: { "content-length": String(10 * 1024 * 1024 + 1) }, body: "x" }), params("attachments"));
  assert.equal(response.status, 413);
  assert.equal(called, false);
});
