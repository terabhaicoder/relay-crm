import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";

// Each test owns a new real workspace. These tests never use an existing user's
// browser context, seed their workspace, or replace API responses with fixtures.
async function createWorkspace(page: Page) {
  const suffix = randomUUID();
  const response = await page.request.post("/api/v1/auth/signup", {
    data: {
      name: "Navigation Reviewer",
      email: `navigation-${suffix}@example.test`,
      password: "Navigation-Password-2026",
      company_name: `Regression workspace ${suffix}`,
    },
  });
  expect(response.status()).toBe(201);
  return suffix;
}

function recordButton(page: Page, name: string) {
  return page.getByRole("button", { name: new RegExp(name) }).first();
}

async function createRecord(page: Page, entity: string, name: string) {
  const response = await page.request.post(`/api/v1/${entity}`, {
    headers: { "Idempotency-Key": randomUUID() },
    data: { name },
  });
  expect(response.status()).toBe(201);
  return (await response.json()) as { id: string };
}

test("workspace navigation retains its shell and rejects late results from another section", async ({
  page,
}) => {
  const suffix = await createWorkspace(page);
  const leadName = `Navigation lead ${suffix}`;
  const contactName = `Delayed contact ${suffix}`;
  const taskName = `Current task ${suffix}`;
  await createRecord(page, "leads", leadName);
  await createRecord(page, "contacts", contactName);
  await createRecord(page, "activities", taskName);

  let authenticationReads = 0;
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/v1/auth/me")
      authenticationReads += 1;
  });
  await page.goto("/dashboard");
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  await expect(navigation).toBeVisible();
  const originalNavigation = await navigation.elementHandle();
  if (!originalNavigation) throw new Error("Workspace navigation did not mount.");
  const readsAfterLogin = authenticationReads;
  const assertSameNavigation = async () => {
    await expect(navigation).toBeVisible();
    expect(
      await originalNavigation.evaluate(
        (element) =>
          element.isConnected &&
          element === document.querySelector('nav[aria-label="Main navigation"]'),
      ),
    ).toBe(true);
    expect(authenticationReads).toBe(readsAfterLogin);
  };

  await navigation.getByRole("link", { name: "Leads", exact: true }).click();
  await expect(recordButton(page, leadName)).toBeVisible();
  await assertSameNavigation();

  let releaseContact!: () => void;
  const release = new Promise<void>((resolve) => { releaseContact = resolve; });
  let contactFetched!: () => void;
  const fetched = new Promise<void>((resolve) => { contactFetched = resolve; });
  let contactDelivered!: () => void;
  const delivered = new Promise<void>((resolve) => { contactDelivered = resolve; });
  const contactsEndpoint = /\/api\/v1\/contacts\?/;
  await page.route(contactsEndpoint, async (route) => {
    // Hold a successful response from the real backend until a later route is
    // showing. Its body and status are never replaced with invented results.
    const response = await route.fetch();
    expect(response.status()).toBe(200);
    contactFetched();
    await release;
    await route.fulfill({ response });
    contactDelivered();
  });
  try {
    const delayedResponse = page.waitForResponse(
      (response) => new URL(response.url()).pathname === "/api/v1/contacts",
    );
    await navigation.getByRole("link", { name: "Contacts", exact: true }).click();
    await fetched;
    await expect(page.getByTestId("section-loading")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Contacts", exact: true })).toBeVisible();
    await expect(recordButton(page, leadName)).toHaveCount(0);
    await assertSameNavigation();

    await navigation.getByRole("link", { name: "My tasks", exact: true }).click();
    await expect(recordButton(page, taskName)).toBeVisible();
    releaseContact();
    await delivered;
    await (await delayedResponse).finished();
    // Let the delivered response and any resulting React update reach a paint
    // before asserting that a stale response did not replace the task list.
    await page.evaluate(() => new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
    }));
    await expect(page.getByRole("heading", { name: "My tasks", exact: true })).toBeVisible();
    await expect(recordButton(page, taskName)).toBeVisible();
    await expect(recordButton(page, contactName)).toHaveCount(0);
    await assertSameNavigation();
  } finally {
    releaseContact();
    await page.unroute(contactsEndpoint);
  }

  await page.goBack();
  await expect(recordButton(page, contactName)).toBeVisible();
  await assertSameNavigation();
  await page.goForward();
  await expect(recordButton(page, taskName)).toBeVisible();
  await assertSameNavigation();
  await navigation.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard(?:\?.*)?$/);
  await assertSameNavigation();
});

test("record Select supports keyboard selection, Escape dismissal and persisted values", async ({
  page,
}) => {
  const suffix = await createWorkspace(page);
  await page.goto("/leads");
  await page.getByRole("button", { name: "Add lead", exact: true }).click();
  const dialog = page.getByRole("dialog");
  const name = `Keyboard lead ${suffix}`;
  await dialog.getByLabel("Full name").fill(name);
  const source = dialog.getByRole("combobox", { name: "Source", exact: true });
  expect(await source.evaluate((element) => element.tagName)).toBe("BUTTON");
  await expect(source).toContainText("Website");
  await source.focus();
  await source.press("ArrowDown");
  await expect(page.getByRole("listbox")).toBeVisible();
  await source.press("End");
  await source.press("Escape");
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await expect(dialog).toBeVisible();
  await expect(source).toBeFocused();
  await expect(source).toContainText("Website");

  await source.press("ArrowDown");
  await source.press("Home");
  await source.press("r");
  await source.press("Enter");
  await expect(source).toContainText("Referral");
  await expect(page.getByRole("listbox")).toHaveCount(0);
  const status = dialog.getByRole("combobox", { name: "Status", exact: true });
  await status.click();
  await page.getByRole("option", { name: "Qualified", exact: true }).click();
  await expect(status).toContainText("Qualified");
  await source.focus();
  await source.press("ArrowDown");
  await source.press("Tab");
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await expect(dialog).toBeVisible();
  await expect(source).not.toBeFocused();

  const saved = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/api/v1/leads" &&
      response.request().method() === "POST",
  );
  await dialog.getByRole("button", { name: "Create lead", exact: true }).click();
  const result = await saved;
  expect(result.status()).toBe(201);
  const record = (await result.json()) as { id: string };
  await expect(dialog).toBeHidden();
  const persisted = await page.request.get(`/api/v1/leads/${record.id}`);
  expect(persisted.status()).toBe(200);
  expect(await persisted.json()).toMatchObject({ name, source: "Referral", status: "Qualified" });
  await recordButton(page, name).click();
  await expect(dialog.getByRole("combobox", { name: "Source", exact: true })).toContainText("Referral");
  await expect(dialog.getByRole("combobox", { name: "Status", exact: true })).toContainText("Qualified");
});

test("named Select submits its role through FormData and resets with the invitation form", async ({
  page,
}) => {
  const suffix = await createWorkspace(page);
  await page.goto("/settings");
  await page.getByRole("button", { name: "Team", exact: true }).click();
  const email = `select-invite-${suffix}@example.test`;
  await page.getByLabel("Invite email", { exact: true }).fill(email);
  const role = page.getByRole("combobox", { name: "Invitation role", exact: true });
  expect(await role.evaluate((element) => element.tagName)).toBe("BUTTON");
  await expect(role).toContainText("Sales Rep");
  await role.focus();
  await role.press("ArrowDown");
  await role.press("End");
  await role.press("Enter");
  await expect(role).toContainText("Read-only");
  const created = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/api/v1/team/invites" &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Create invitation link", exact: true }).click();
  const response = await created;
  expect(response.status()).toBe(201);
  expect(await response.json()).toMatchObject({ email, role: "Read-only" });
  await expect(page.getByLabel("Private invitation link", { exact: true })).toBeVisible();
  await expect(role).toContainText("Sales Rep");
  await expect(page.getByLabel("Invite email", { exact: true })).toHaveValue("");
});

test("activity relationship can be cleared with None and stays cleared after reload", async ({ page }) => {
  const suffix = await createWorkspace(page);
  const lead = await createRecord(page, "leads", `QA relationship ${suffix}`);
  const response = await page.request.post("/api/v1/activities", {
    headers: { "Idempotency-Key": randomUUID() },
    data: { name: `QA unlinked task ${suffix}`, entity_type: "leads", entity_id: lead.id },
  });
  expect(response.status()).toBe(201);
  const task = await response.json() as { id: string };
  await page.goto(`/activities?id=${task.id}`);
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("combobox", { name: "Related record type", exact: true }).click();
  await page.getByRole("option", { name: "None", exact: true }).click();
  await expect(dialog.getByRole("combobox", { name: "Select related record", exact: true })).toBeDisabled();
  const saved = page.waitForResponse(response => response.url().includes(`/activities/${task.id}`) && response.request().method() === "PATCH");
  await dialog.getByRole("button", { name: "Save changes", exact: true }).click();
  expect((await saved).status()).toBe(200);
  const persisted = await page.request.get(`/api/v1/activities/${task.id}`);
  expect(await persisted.json()).toMatchObject({ entity_type: null, entity_id: null });
  await page.reload();
  await expect(page.getByRole("dialog").getByRole("combobox", { name: "Related record type", exact: true })).toContainText("None");
});

test("ticket assignment persists and email drafts have no unavailable send action", async ({ page }) => {
  const suffix = await createWorkspace(page);
  const memberResponse = await page.request.post("/api/v1/team", {
    data: { name: "QA Support Teammate", email: `qa-support-${suffix}@example.test`, password: "Navigation-Password-2026", role: "Support Agent" },
  });
  expect(memberResponse.status()).toBe(201);
  const member = await memberResponse.json() as { id: string };
  await page.goto("/tickets");
  await page.getByRole("button", { name: "Add ticket", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Subject", { exact: false }).fill(`QA assigned ticket ${suffix}`);
  await dialog.getByRole("combobox", { name: "Assigned to", exact: true }).click();
  await page.getByRole("option", { name: "QA Support Teammate", exact: true }).click();
  const saved = page.waitForResponse(response => new URL(response.url()).pathname === "/api/v1/tickets" && response.request().method() === "POST");
  await dialog.getByRole("button", { name: "Create ticket", exact: true }).click();
  const response = await saved;
  expect(response.status()).toBe(201);
  const ticket = await response.json() as { id: string; owner_id: string };
  expect(ticket.owner_id).toBe(member.id);
  const persisted = await page.request.get(`/api/v1/tickets/${ticket.id}`);
  expect(await persisted.json()).toMatchObject({ owner_id: member.id });
  const draftResponse = await page.request.post("/api/v1/email/messages", {
    headers: { "Idempotency-Key": randomUUID() },
    data: { recipient: "qa-draft@example.test", subject: "QA unsent draft", body: "Draft only" },
  });
  expect(draftResponse.status()).toBe(201);
  const draft = await draftResponse.json() as { id: string };
  await page.goto(`/communications?id=${draft.id}`);
  await expect(page.getByRole("dialog")).toContainText("This draft has not been sent.");
  await expect(page.getByRole("button", { name: "Send email", exact: true })).toHaveCount(0);
});

test("attachments retry failed listing and lost upload acknowledgement without duplication", async ({ page }) => {
  const suffix = await createWorkspace(page);
  const lead = await createRecord(page, "leads", `QA attachment retry ${suffix}`);
  let failList = true;
  let loseAcknowledgement = true;
  await page.route("**/api/v1/attachments?**", async route => {
    if (route.request().method() === "GET" && failList) {
      failList = false;
      await route.abort("failed");
    } else if (route.request().method() === "POST" && loseAcknowledgement) {
      // Persist with the real backend, then simulate a connection loss before
      // the browser sees success. Retry must recover the same attachment.
      loseAcknowledgement = false;
      const response = await route.fetch();
      expect(response.status()).toBe(201);
      await route.abort("failed");
    } else {
      await route.continue();
    }
  });
  await page.goto(`/leads?id=${lead.id}`);
  const attachmentSection = page.getByRole("dialog").locator("section").filter({ has: page.getByRole("heading", { name: "Attachments", exact: true }) });
  await attachmentSection.getByRole("button", { name: "Retry attachments", exact: true }).click();
  await expect(attachmentSection.getByRole("alert")).toHaveCount(0);
  await expect(attachmentSection).toContainText("No attachments yet.");
  await attachmentSection.locator('input[type="file"]').setInputFiles({
    name: "QA-retry.txt", mimeType: "text/plain", buffer: Buffer.from("Real attachment retry evidence"),
  });
  await attachmentSection.getByRole("button", { name: "Retry upload", exact: true }).click();
  await expect(attachmentSection.getByRole("alert")).toHaveCount(0);
  await expect(attachmentSection.getByRole("link", { name: /QA-retry.txt/ })).toHaveCount(1);
  const persisted = await page.request.get(`/api/v1/attachments?entity_type=leads&entity_id=${lead.id}`);
  const list = await persisted.json() as { items: { id: string; filename: string }[] };
  expect(list.items).toHaveLength(1);
  expect(list.items[0]?.filename).toBe("QA-retry.txt");
});

test("native date submission persists picker values and explicit clearing after reload", async ({ page }) => {
  const suffix = await createWorkspace(page);
  const task = await createRecord(page, "activities", `QA native date ${suffix}`);
  await page.goto(`/activities?id=${task.id}`);
  let dialog = page.getByRole("dialog");
  let due = dialog.getByLabel("Due date", { exact: true });
  await due.fill("2026-10-12");
  // Reproduce native picker/autofill committing a value without React's change
  // event. The submitted value must be the visible date, not stale React state.
  await due.evaluate((input: HTMLInputElement) => { input.value = "2026-10-13"; });
  await due.press("Tab");
  const saved = page.waitForResponse(response => response.url().includes(`/activities/${task.id}`) && response.request().method() === "PATCH");
  await dialog.getByRole("button", { name: "Save changes", exact: true }).click();
  expect((await saved).status()).toBe(200);
  const persisted = await page.request.get(`/api/v1/activities/${task.id}`);
  expect((await persisted.json()).due_date).toMatch(/^2026-10-13/);
  await page.reload();
  dialog = page.getByRole("dialog");
  due = dialog.getByLabel("Due date", { exact: true });
  await expect(due).toHaveValue("2026-10-13");
  await due.fill("");
  const cleared = page.waitForResponse(response => response.url().includes(`/activities/${task.id}`) && response.request().method() === "PATCH");
  await dialog.getByRole("button", { name: "Save changes", exact: true }).click();
  expect((await cleared).status()).toBe(200);
  const clearedRecord = await page.request.get(`/api/v1/activities/${task.id}`);
  expect((await clearedRecord.json()).due_date).toBeNull();
  await page.reload();
  await expect(page.getByRole("dialog").getByLabel("Due date", { exact: true })).toHaveValue("");
});
