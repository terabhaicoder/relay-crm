import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";

type RecordResponse = { id: string; [key: string]: unknown };
async function workspace(page: Page) {
  const suffix = randomUUID();
  const response = await page.request.post("/api/v1/auth/signup", { data: {
    name: "CRM Coverage Reviewer", email: `crm-coverage-${suffix}@example.test`,
    password: "CRM-Coverage-2026", company_name: `QA CRM coverage ${suffix}`,
  } });
  expect(response.status()).toBe(201);
}
async function create(page: Page, entity: string, data: Record<string, unknown>): Promise<RecordResponse> {
  const response = await page.request.post(`/api/v1/${entity}`, {
    headers: { "Idempotency-Key": randomUUID() }, data,
  });
  expect(response.status()).toBe(201);
  return await response.json() as RecordResponse;
}

// The default Playwright configuration uses a disposable SQLite workspace.
// Setup uses real API records; UI operations never replace backend responses.
test("customer overview connects contacts and creates a persisted company follow-up", async ({ page }) => {
  const duplicateKeys: string[] = [];
  page.on("console", message => { if (message.text().includes("same key")) duplicateKeys.push(message.text()); });
  await workspace(page);
  const company = await create(page, "parties", { name: "QA Connected Customer" });
  const contact = await create(page, "contacts", { name: "QA Customer Contact", party_id: company.id, email: "contact@example.test" });
  await page.goto(`/accounts?id=${company.id}`);
  let dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Customer overview", exact: true }).click();
  const context = dialog.getByRole("region", { name: "Customer overview", exact: true });
  await expect(context.getByText("Loading customer context…")).toBeHidden();
  await context.getByRole("tab", { name: /^Contacts/ }).click();
  await expect(context.getByRole("link", { name: /QA Customer Contact/ })).toHaveAttribute("href", `/contacts?id=${contact.id}`);
  await context.getByRole("button", { name: "Add follow-up", exact: true }).click();
  dialog = page.getByRole("dialog");
  // Consuming ?new=1 must not collide with the empty-ID editor key and
  // leave duplicate drawers after React reconciles the route update.
  await expect(page).toHaveURL(/\/activities$/);
  await expect(dialog).toHaveCount(1);
  await expect(dialog.getByRole("heading", { name: "New task", exact: true })).toBeVisible();
  await expect(dialog.getByRole("combobox", { name: "Related record type", exact: true })).toContainText("parties");
  await dialog.getByLabel("What needs to happen?").fill("QA Customer onboarding call");
  await dialog.getByRole("button", { name: "Create task", exact: true }).click();
  await expect(dialog).toBeHidden();
  const response = await page.request.get(`/api/v1/activities?entity_type=parties&entity_id=${company.id}`);
  expect(response.ok()).toBe(true);
  const tasks = await response.json() as { total: number; items: RecordResponse[] };
  expect(tasks.total).toBe(1);
  expect(tasks.items[0]).toMatchObject({ name: "QA Customer onboarding call", entity_type: "parties", entity_id: company.id });
  await page.goto(`/accounts?id=${company.id}`);
  dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Customer overview", exact: true }).click();
  await dialog.getByRole("tab", { name: /^Activities/ }).click();
  await expect(dialog.getByRole("link", { name: /QA Customer onboarding call/ })).toBeVisible();
  await dialog.getByRole("button", { name: "Add follow-up", exact: true }).click();
  await expect(page).toHaveURL(/\/activities$/);
  await expect(dialog).toHaveCount(1);
  await expect(dialog.getByLabel("What needs to happen?")).toHaveValue("");
  await dialog.getByRole("button", { name: "Close record", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(duplicateKeys).toEqual([]);
});

test("campaign member search, duplicate-safe addition, conversion totals and removal persist", async ({ page }) => {
  await workspace(page);
  const campaign = await create(page, "campaigns", { name: "QA Connected Campaign" });
  const lead = await create(page, "leads", { name: "QA Campaign Prospect", company: "QA Prospect Company" });
  await page.goto(`/campaigns?id=${campaign.id}`);
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Members", exact: true }).click();
  const members = dialog.getByRole("region", { name: "Campaign members", exact: true });
  for (let addition = 0; addition < 2; addition += 1) {
    await members.getByLabel("Find a lead", { exact: true }).fill("QA Campaign Prospect");
    await members.getByRole("button", { name: /QA Campaign Prospect/ }).click();
    await members.getByRole("button", { name: "Add member", exact: true }).click();
    await expect(members.getByText("QA Campaign Prospect is a campaign member.", { exact: true })).toBeVisible();
    await expect(members.getByRole("link", { name: /QA Campaign Prospect/ })).toHaveCount(1);
  }
  let response = await page.request.get(`/api/v1/campaigns/${campaign.id}/members`);
  expect(response.ok()).toBe(true);
  expect(await response.json()).toMatchObject({ total: 1, summary: { members: 1, leads: 1, converted_leads: 0 } });
  const conversion = await page.request.post(`/api/v1/leads/${lead.id}/convert`, { data: { create_deal: false } });
  expect(conversion.ok()).toBe(true);
  await page.reload();
  await dialog.getByRole("button", { name: "Members", exact: true }).click();
  await expect(members.getByText("100%", { exact: true })).toBeVisible();
  await expect(members.getByRole("link", { name: /QA Campaign Prospect/ })).toContainText("Converted");
  await members.getByRole("button", { name: "Remove QA Campaign Prospect from campaign", exact: true }).click();
  await members.getByRole("button", { name: "Remove member", exact: true }).click();
  await expect(members.getByText("No members yet.", { exact: false })).toBeVisible();
  response = await page.request.get(`/api/v1/campaigns/${campaign.id}/members`);
  expect(await response.json()).toMatchObject({ total: 0 });
  expect((await page.request.get(`/api/v1/leads/${lead.id}`)).status()).toBe(200);
});

test("pipeline settings creates, edits and exposes a real sales process on the board", async ({ page }) => {
  await workspace(page);
  await page.goto("/pipelines");
  const settings = page.getByRole("region", { name: "Pipeline settings", exact: true });
  await settings.getByRole("button", { name: "New pipeline", exact: true }).click();
  await settings.getByLabel("Pipeline name", { exact: true }).fill("QA Enterprise Sales");
  await settings.getByLabel("Stage 1 name", { exact: true }).fill("Research");
  await settings.getByRole("button", { name: "Create pipeline", exact: true }).click();
  await expect(settings.getByRole("status")).toContainText("Pipeline created.");
  await settings.getByLabel("Research probability", { exact: true }).fill("35");
  await settings.getByRole("button", { name: "Add stage", exact: true }).click();
  await settings.getByLabel("Stage 5 name", { exact: true }).fill("Legal review");
  await settings.getByRole("button", { name: "Save pipeline", exact: true }).click();
  await expect(settings.getByRole("status")).toContainText("Pipeline saved.");
  const response = await page.request.get("/api/v1/pipelines");
  const payload = await response.json() as { items: { id: string; name: string; stages: { id: string; name: string; probability: number }[] }[] };
  const pipeline = payload.items.find(item => item.name === "QA Enterprise Sales");
  expect(pipeline?.stages).toEqual(expect.arrayContaining([expect.objectContaining({ name: "Research", probability: 35, category: "open" })]));
  expect(pipeline?.stages.some(stage => stage.name === "Legal review")).toBe(true);
  const research = pipeline?.stages.find(stage => stage.name === "Research");
  if (!pipeline || !research) throw new Error("Saved pipeline did not retain its Research stage.");
  await create(page, "deals", { name: "QA Enterprise Opportunity", pipeline_id: pipeline.id, stage_id: research.id, amount: "42000" });
  await page.goto("/deals");
  await page.getByRole("combobox", { name: "Sales pipeline", exact: true }).click();
  await page.getByRole("option", { name: "QA Enterprise Sales", exact: true }).click();
  const researchColumn = page.getByRole("region", { name: "Research deals", exact: true });
  await expect(researchColumn).toBeVisible();
  await expect(researchColumn.getByRole("button", { name: /QA Enterprise Opportunity/ })).toBeVisible();
  await expect(page.getByRole("region", { name: "Legal review deals", exact: true })).toBeVisible();
});

test("calendar counts every activity and paginates beyond the first 20 with consistent search", async ({ page }) => {
  await workspace(page);
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
  for (let index = 0; index < 25; index += 1) {
    await create(page, "activities", { name: `QA Calendar ${String(index + 1).padStart(2, "0")}`, due_date: today });
  }
  await page.goto("/calendar");
  const calendar = page.getByRole("region", { name: "Activity calendar", exact: true });
  const agenda = page.getByRole("region", { name: "Selected day activities", exact: true });
  await expect(calendar.getByRole("button", { name: `${today}, 25 activities`, exact: true })).toBeVisible();
  await expect(agenda.getByText("1–20 of 25", { exact: true })).toBeVisible();
  await agenda.getByRole("button", { name: "Next activities", exact: true }).click();
  await expect(agenda.getByText("21–25 of 25", { exact: true })).toBeVisible();
  await page.getByRole("textbox", { name: "Search calendar", exact: true }).fill("QA Calendar 25");
  await expect(calendar.getByRole("button", { name: `${today}, 1 activities`, exact: true })).toBeVisible();
  await expect(agenda.getByText("1–1 of 1", { exact: true })).toBeVisible();
  await expect(agenda.getByRole("button", { name: /QA Calendar 25/ })).toBeVisible();
});
