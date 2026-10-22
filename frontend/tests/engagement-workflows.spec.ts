import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";

async function signup(page: Page) {
  const key = randomUUID();
  const response = await page.request.post("/api/v1/auth/signup", { data: { name: "Engagement reviewer", email: `engagement-${key}@example.test`, password: "Engagement-2026", company_name: `QA Engagement ${key}` } });
  expect(response.status()).toBe(201);
}

test("record-linked email uses a template and preserves its relationship through editing", async ({ page }, testInfo) => {
  await signup(page);
  const leadResponse = await page.request.post("/api/v1/leads", { data: { name: "QA Template Customer", email: "template-customer@example.test", company: "QA Company" } });
  expect(leadResponse.status()).toBe(201);
  const lead = await leadResponse.json() as { id: string };
  const templateResponse = await page.request.post("/api/v1/email/templates", { data: { name: "QA Personal follow-up", subject: "Hello {{name}}", body: "Thanks for talking about {{company}}. Reply to {{email}}." } });
  expect(templateResponse.status()).toBe(201);
  await page.goto(`/leads?id=${lead.id}`);
  await page.getByRole("dialog").getByRole("button", { name: "Prepare email draft", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toHaveCount(1);
  await expect(dialog.getByLabel(/^To(?: \*)?$/)).toHaveValue("template-customer@example.test");
  await dialog.getByRole("combobox", { name: "Email template", exact: true }).click();
  await page.getByRole("option", { name: "QA Personal follow-up", exact: true }).click();
  await dialog.getByRole("button", { name: "Apply template", exact: true }).click();
  await expect(dialog.getByLabel(/^Subject(?: \*)?$/)).toHaveValue("Hello QA Template Customer");
  await expect(dialog.getByRole("textbox", { name: /^Message/ })).toHaveValue("Thanks for talking about QA Company. Reply to template-customer@example.test.");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: testInfo.outputPath("linked-email-desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath("linked-email-mobile.png"), fullPage: true });
  await expect(page.locator("body")).toHaveJSProperty("scrollWidth", 390);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await dialog.getByRole("button", { name: "Create email", exact: true }).click();
  await expect(dialog).toBeHidden();
  const list = await (await page.request.get("/api/v1/email/messages")).json() as { items: { id: string; entity_type: string; entity_id: string; status: string }[] };
  expect(list.items).toHaveLength(1);
  expect(list.items[0]).toMatchObject({ entity_type: "leads", entity_id: lead.id, status: "draft" });
  await page.goto(`/leads?id=${lead.id}`);
  const linked = dialog.getByRole("region", { name: "Linked email drafts", exact: true });
  await expect(linked.getByRole("link", { name: "Hello QA Template Customer", exact: true })).toHaveAttribute("href", `/communications?id=${list.items[0]!.id}`);
  await linked.getByRole("link", { name: "Hello QA Template Customer", exact: true }).click();
  await dialog.getByLabel(/^Subject(?: \*)?$/).fill("Reviewed follow-up");
  await dialog.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(dialog).toBeHidden();
  const updated = await page.request.get(`/api/v1/email/messages/${list.items[0]!.id}`);
  expect(updated.status()).toBe(200);
  expect(await updated.json()).toMatchObject({ subject: "Reviewed follow-up", entity_type: "leads", entity_id: lead.id, status: "draft" });
});

test("all automation events are selectable and lead-update automation creates a linked follow-up", async ({ page }) => {
  await signup(page);
  const leadResponse = await page.request.post("/api/v1/leads", { data: { name: "QA Automated Lead" } });
  const lead = await leadResponse.json() as { id: string; version: number };
  await page.goto("/automations?new=1");
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel(/^Automation name(?: \*)?$/).fill("Follow up after qualification");
  await dialog.getByLabel(/^Task or notification text(?: \*)?$/).fill("Call {{name}} after qualification");
  await dialog.getByRole("combobox", { name: "Trigger", exact: true }).click();
  for (const trigger of ["leads.created", "leads.updated", "leads.converted", "deals.created", "deals.won", "deals.lost", "deals.stage_changed", "tickets.created", "tickets.updated", "activities.created", "activities.completed"]) {
    await expect(page.getByRole("option", { name: trigger, exact: true })).toHaveCount(1);
  }
  await page.getByRole("option", { name: "leads.updated", exact: true }).click();
  await dialog.getByRole("button", { name: "Add condition", exact: true }).click();
  await dialog.getByLabel("Condition 1 value", { exact: true }).fill("Qualified");
  await dialog.getByRole("button", { name: "Create automation", exact: true }).click();
  await expect(dialog).toBeHidden();
  const update = await page.request.patch(`/api/v1/leads/${lead.id}`, { data: { status: "Qualified", version: lead.version } });
  expect(update.status()).toBe(200);
  const result = await (await page.request.get(`/api/v1/activities?entity_type=leads&entity_id=${lead.id}`)).json() as { total: number; items: { name: string }[] };
  expect(result.total).toBe(1);
  expect(result.items[0]!.name).toBe("Call QA Automated Lead after qualification");
});
