import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

test("CSV UI persists 980 of 1000 rows, downloads actual errors, retries safely and exports every page", async ({ page }) => {
  test.setTimeout(180_000);
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const signup = await page.request.post("/api/v1/auth/signup", { data: {
    name: "Disposable Import QA", company_name: `Disposable import QA ${suffix}`,
    email: `import-${suffix}@example.test`, password: "Disposable-Import-QA-2026",
  } });
  expect(signup.status()).toBe(201);
  await page.goto("/leads");
  const csv = ["name,email,phone,company,value,notes", ...Array.from({ length: 1000 }, (_, i) =>
    `QA Import ${String(i).padStart(4, "0")},${i < 20 ? "invalid-email" : `qa${i}@example.test`},+9191${String(i).padStart(8, "0")},"QA शांति, Components",123.45,"Line one\nLine two"`
  )].join("\n");
  const upload = { name: "qa-1000.csv", mimeType: "text/csv", buffer: Buffer.from(csv) };
  await page.getByLabel("Import CSV file", { exact: true }).setInputFiles(upload);
  await expect(page.locator(".import-report")).toContainText("980 created, 0 skipped, 20 errors", { timeout: 90_000 });
  const list = await (await page.request.get("/api/v1/leads?limit=100&sort=name&order=asc")).json();
  expect(list.total).toBe(980);
  expect(list.items[0]).toMatchObject({ name: "QA Import 0020", phone: "+919100000020", company: "QA शांति, Components", value: "123.45", notes: "Line one\nLine two" });
  const errorsPending = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download error report", exact: true }).click();
  const errors = await errorsPending;
  const errorText = await readFile((await errors.path())!, "utf8");
  expect(errorText).toContain("row,name,message");
  expect(errorText.match(/QA Import \d{4}/g)).toHaveLength(20);
  await page.getByLabel("Import CSV file", { exact: true }).setInputFiles(upload);
  await expect(page.locator(".import-report")).toContainText("0 created, 980 skipped, 20 errors", { timeout: 90_000 });
  const exportPending = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export", exact: true }).click();
  const exported = await exportPending;
  const exportedText = await readFile((await exported.path())!, "utf8");
  expect(exportedText.match(/QA Import \d{4}/g)).toHaveLength(980);
  expect(exportedText).toContain("'+919100000020");
  expect(exportedText).toContain('"QA शांति, Components"');
  await page.getByRole("textbox", { name: "Search leads", exact: true }).fill("QA Import 0020");
  await expect(page.getByText("1–1 of 1 records", { exact: true })).toBeVisible();
  const filteredPending = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export", exact: true }).click();
  const filtered = await filteredPending;
  const filteredText = await readFile((await filtered.path())!, "utf8");
  expect(filteredText.match(/QA Import \d{4}/g)).toHaveLength(1);
});
