import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

// The saved-view bar was intentionally removed from the CRM lists. Preserve this
// historical journey until a new UI entry point exists; the retained API is
// covered by backend/tests/test_saved_views.py.
test.skip("personal view saves real filters, restores after reload, updates and deletes", async ({ page }, testInfo) => {
  const suffix = randomUUID();
  const signup = await page.request.post("/api/v1/auth/signup", { data: {
    name: "Saved view reviewer", email: `views-${suffix}@example.test`,
    password: "Saved-Views-2026", company_name: `QA Saved views ${suffix}`,
  } });
  expect(signup.status()).toBe(201);
  const lead = await page.request.post("/api/v1/leads", { data: { name: "Preferred buyer", status: "Qualified" } });
  expect(lead.status()).toBe(201);
  await page.goto("/leads");
  await page.getByPlaceholder("Search leads…", { exact: true }).fill("Preferred");
  await page.getByRole("combobox", { name: "Filter by status", exact: true }).click();
  await page.getByRole("option", { name: "Qualified", exact: true }).click();
  await page.getByRole("combobox", { name: "Sort records", exact: true }).click();
  await page.getByRole("option", { name: "Name: A to Z", exact: true }).click();
  const views = page.getByRole("region", { name: "Personal saved views", exact: true });
  await views.getByRole("button", { name: "Save current view", exact: true }).click();
  await views.getByLabel("View name", { exact: true }).fill("My qualified buyers");
  await views.getByRole("button", { name: "Save view", exact: true }).click();
  await expect(views.getByRole("status")).toContainText("Saved “My qualified buyers” for you.");
  let result = await (await page.request.get("/api/v1/saved-views?entity=leads")).json() as { total: number; items: { id: string; name: string; filters: { q: string; status: string; sort: string } }[] };
  expect(result.total).toBe(1);
  expect(result.items[0]!.filters).toMatchObject({ q: "Preferred", status: "Qualified", sort: "name:asc" });
  await page.reload();
  await views.getByRole("combobox", { name: "Saved view", exact: true }).click();
  await page.getByRole("option", { name: "My qualified buyers", exact: true }).click();
  await expect(page.getByPlaceholder("Search leads…", { exact: true })).toHaveValue("Preferred");
  await expect(page.getByRole("combobox", { name: "Filter by status", exact: true })).toContainText("Qualified");
  await expect(page.getByRole("combobox", { name: "Sort records", exact: true })).toContainText("Name: A to Z");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath("saved-views-mobile.png"), fullPage: true });
  await expect(page.locator("body")).toHaveJSProperty("scrollWidth", 390);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByPlaceholder("Search leads…", { exact: true }).fill("buyer");
  await views.getByRole("button", { name: "Save current view", exact: true }).click();
  await views.getByLabel("View name", { exact: true }).fill("Updated buyers");
  await views.getByRole("button", { name: "Update view", exact: true }).click();
  await expect(views.getByRole("status")).toContainText("Saved “Updated buyers” for you.");
  result = await (await page.request.get("/api/v1/saved-views?entity=leads")).json();
  expect(result.total).toBe(1);
  expect(result.items[0]!.name).toBe("Updated buyers");
  expect(result.items[0]!.filters.q).toBe("buyer");
  await views.getByRole("button", { name: "Delete saved view", exact: true }).click();
  await views.getByRole("button", { name: "Delete view", exact: true }).click();
  await expect(views.getByRole("status")).toContainText("Deleted “Updated buyers”.");
  expect((await (await page.request.get("/api/v1/saved-views?entity=leads")).json()).total).toBe(0);
  await expect(page.getByPlaceholder("Search leads…", { exact: true })).toHaveValue("buyer");
});
