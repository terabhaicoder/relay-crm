import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

test("forecast shows complete date-based totals, paginates and opens the exact deal", async ({ page }) => {
  const suffix = randomUUID();
  const signup = await page.request.post("/api/v1/auth/signup", { data: {
    name: "Forecast Reviewer", company_name: "Fictional Forecast QA",
    email: `forecast-${suffix}@example.test`, password: "Forecast-Test-2026!",
  } });
  expect(signup.status()).toBe(201);
  for (let index = 0; index < 22; index++) {
    const created = await page.request.post("/api/v1/deals", {
      headers: { "Idempotency-Key": randomUUID() },
      data: { name: `Forecast opportunity ${String(index).padStart(2, "0")}`, amount: "100.05", expected_close_date: `2026-10-${String(index + 1).padStart(2, "0")}` },
    });
    expect(created.status()).toBe(201);
  }
  expect((await page.request.post("/api/v1/deals", { data: { name: "Unscheduled opportunity", amount: "800" } })).status()).toBe(201);
  await page.goto("/reports");
  const report = page.getByRole("region", { name: "Sales forecast", exact: true });
  await report.getByLabel("Forecast from", { exact: true }).fill("2026-10-01");
  await report.getByLabel("Forecast to", { exact: true }).fill("2026-10-31");
  await expect(report.getByText("₹2,201.1", { exact: true })).toBeVisible();
  const details = report.getByRole("region", { name: "Forecast deals", exact: true });
  await expect(details.getByText("22 matching deals", { exact: true })).toBeVisible();
  await expect(details.getByRole("link", { name: /^Forecast opportunity/ })).toHaveCount(20);
  await details.getByRole("button", { name: "Next", exact: true }).click();
  await expect(details.getByRole("link", { name: /^Forecast opportunity/ })).toHaveCount(2);
  await details.getByRole("button", { name: "Missing close date", exact: true }).click();
  await expect(details.getByRole("link", { name: "Unscheduled opportunity", exact: true })).toBeVisible();
  await details.getByRole("link", { name: "Unscheduled opportunity", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "Unscheduled opportunity", exact: true })).toBeVisible();
});
