import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = readFileSync(new URL("../src/lib/api/client.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const compiledModule = { exports: {} };
vm.runInNewContext(compiled, { module: compiledModule, exports: compiledModule.exports, Intl, crypto: { randomUUID } });
const { amount, formatTimestamp, submittedDate, idempotencyRequest } = compiledModule.exports;

test("currency keeps paise visible with Indian grouping", () => {
  assert.equal(amount("123456.78"), "₹1,23,456.78");
  assert.equal(amount("0.01"), "₹0.01");
  assert.equal(amount("25000.00"), "₹25,000");
  assert.equal(amount("999999999999.99"), "₹9,99,99,99,99,999.99");
});

test("UTC timestamps display explicit India time without changing date-only values", () => {
  assert.equal(formatTimestamp("2026-10-12T07:30:00Z"), "12 Oct 2026, 13:00 IST");
  assert.equal(formatTimestamp("2026-10-12T07:30:00"), "12 Oct 2026, 13:00 IST");
  assert.equal(formatTimestamp("2026-10-12T18:45:00+00:00"), "13 Oct 2026, 00:15 IST");
  assert.equal(formatTimestamp("2026-10-13"), "2026-10-13");
  assert.equal(formatTimestamp(null), "—");
  assert.equal(formatTimestamp("invalid date"), "invalid date");
});

test("date-only controls preserve an existing time on unrelated edits and honor changed or cleared days", () => {
  const existing = "2026-10-13T09:45:30+00:00";
  assert.equal(submittedDate("2026-10-13", existing), existing);
  assert.equal(submittedDate("2026-10-14", existing), "2026-10-14");
  assert.equal(submittedDate("", existing), null);
  assert.equal(submittedDate("2026-10-13", null), "2026-10-13");
  assert.equal(submittedDate("2026-10-13", "2026-10-13"), "2026-10-13");
});

test("template retries reuse their request key, while changed content and new submissions get new keys", () => {
  const payload = { name: "QA template", subject: "Hello", body: "Welcome" };
  const first = idempotencyRequest(payload, null);
  assert.equal(idempotencyRequest({ ...payload }, first).key, first.key);
  const changed = idempotencyRequest({ ...payload, body: "Changed welcome" }, first);
  assert.notEqual(changed.key, first.key);
  assert.equal(idempotencyRequest({ ...payload, body: "Changed welcome" }, changed).key, changed.key);
  assert.notEqual(idempotencyRequest(payload, null).key, first.key);
});
