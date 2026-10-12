import { expect, test } from "@playwright/test";

test("real signup, lead conversion, linked records, deal win, task, and support note", async ({
  page,
}) => {
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2, 7)}`;
  await page.goto("/dashboard");
  await page
    .getByRole("button", { name: "Create a workspace", exact: true })
    .click();
  await page.getByLabel("Your name", { exact: true }).fill("Journey Owner");
  await page
    .getByLabel("Company name", { exact: true })
    .fill(`Journey ${suffix}`);
  await page.getByLabel("Work email").fill(`owner-${suffix}@example.test`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Journey-Password-2026");
  await page
    .getByRole("button", { name: "Create workspace", exact: true })
    .click();
  await expect(
    page.getByRole("navigation", { name: "Main navigation" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /Good .+, Journey\./ }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Leads", exact: true }).click();
  await page.getByRole("button", { name: "Add lead", exact: true }).click();
  let dialog = page.getByRole("dialog");
  await dialog.getByLabel("Full name").fill("Nisha Customer");
  await dialog
    .getByLabel("Company", { exact: true })
    .fill("Customer Components");
  await dialog.getByLabel("Email", { exact: true }).fill("nisha@example.test");
  await dialog.getByLabel("Phone", { exact: true }).fill("+919876543210");
  await dialog.getByLabel("Estimated value (₹)").fill("25000");
  await dialog
    .getByRole("button", { name: "Create lead", exact: true })
    .click();
  await expect(dialog).toBeHidden();
  await page
    .getByRole("button", { name: /Nisha Customer/ })
    .first()
    .click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByRole("button", { name: "Convert lead", exact: true })
    .click();
  await expect(dialog).toBeHidden();
  await expect(page.getByText("Converted", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Contacts", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /Nisha Customer/ }).first(),
  ).toBeVisible();
  await page.getByRole("link", { name: "Companies", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /Customer Components/ }).first(),
  ).toBeVisible();
  await page.getByRole("link", { name: "Pipeline", exact: true }).click();
  await page
    .getByRole("region", { name: "Discovery deals", exact: true })
    .getByRole("button", { name: /Customer Components opportunity/ })
    .click();
  dialog = page.getByRole("dialog");
  await expect(
    dialog.getByRole("link", { name: "Open linked record" }).first(),
  ).toBeVisible();
  await dialog.getByRole("button", { name: "Mark won", exact: true }).click();
  await expect(dialog).toBeHidden();

  await page.getByRole("link", { name: "My tasks", exact: true }).click();
  await page.getByRole("button", { name: "Add task", exact: true }).click();
  dialog = page.getByRole("dialog");
  await dialog.getByLabel("What needs to happen?").fill("Send onboarding pack");
  await dialog
    .getByRole("button", { name: "Create task", exact: true })
    .click();
  await expect(dialog).toBeHidden();
  await page
    .getByRole("button", { name: "Complete Send onboarding pack", exact: true })
    .click();
  await expect(page.getByText("completed", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Support", exact: true }).click();
  await page.getByRole("button", { name: "Add ticket", exact: true }).click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Subject", { exact: true })
    .fill("Help with customer onboarding");
  await dialog
    .getByLabel("Description", { exact: true })
    .fill("Customer needs a product walkthrough.");
  await dialog
    .getByRole("button", { name: "Create ticket", exact: true })
    .click();
  await expect(dialog).toBeHidden();
  await page
    .getByRole("button", { name: /Help with customer onboarding/ })
    .first()
    .click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Message", { exact: true })
    .fill("Sales handoff is complete.");
  await dialog
    .getByRole("button", { name: "Add internal note", exact: true })
    .click();
  await expect(dialog.getByText("Sales handoff is complete.")).toBeVisible();
  await dialog
    .getByRole("button", { name: "Close record", exact: true })
    .click();

  await page.reload();
  await expect(
    page.getByRole("navigation", { name: "Main navigation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
});

test("mobile sign-up screen fits and labels remain accessible", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
  await expect(page.getByLabel("Work email")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("invitation link joins the correct workspace with read-only controls", async ({
  page,
  browser,
}) => {
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  const owner = await page.request.post("/api/v1/auth/signup", {
    data: {
      name: "Invite Owner",
      email: `invite-owner-${suffix}@example.test`,
      password: "Invite-Password-2026",
      company_name: `Invited Workspace ${suffix}`,
    },
  });
  expect(owner.status()).toBe(201);
  await page.goto("/settings");
  await page.getByRole("button", { name: "Team", exact: true }).click();
  await page
    .getByLabel("Invite email", { exact: true })
    .fill(`invitee-${suffix}@example.test`);
  await page
    .getByRole("combobox", { name: "Invitation role", exact: true })
    .click();
  await page.getByRole("option", { name: "Read-only", exact: true }).click();
  await page
    .getByRole("button", { name: "Create invitation link", exact: true })
    .click();
  const invitationLink = page.getByLabel("Private invitation link", {
    exact: true,
  });
  await expect(invitationLink).toBeVisible();
  const url = await invitationLink.inputValue();
  const context = await browser.newContext();
  const invitedPage = await context.newPage();
  await invitedPage.goto(url);
  await expect(
    invitedPage.getByRole("heading", {
      name: `Join Invited Workspace ${suffix}`,
    }),
  ).toBeVisible();
  await invitedPage
    .getByLabel("Your name", { exact: true })
    .fill("Invited Reviewer");
  await invitedPage
    .getByLabel("Create password", { exact: true })
    .fill("Reviewer-Password-2026");
  await invitedPage
    .getByRole("button", { name: "Join workspace", exact: true })
    .click();
  await expect(
    invitedPage.getByRole("navigation", { name: "Main navigation" }),
  ).toBeVisible();
  await expect(
    invitedPage.getByRole("button", { name: "Add lead", exact: true }),
  ).toBeDisabled();
  await invitedPage.getByRole("link", { name: "Leads", exact: true }).click();
  await expect(
    invitedPage.getByRole("button", { name: "Add lead", exact: true }),
  ).toHaveCount(0);
  const rejected = await invitedPage.request.post(
    new URL("/api/v1/leads", url).toString(),
    { data: { name: "Forbidden write" } },
  );
  expect(rejected.status()).toBe(403);
  await invitedPage.goto(url);
  await expect(invitedPage.getByRole("alert")).toContainText(
    "expired or has already been used",
  );
  await context.close();
});

test("switching accounts clears the previous workspace before new data arrives", async ({
  page,
  browser,
  baseURL,
}) => {
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  const privateDeal = `Private first-workspace deal ${suffix}`;
  const password = "Workspace-Password-2026";
  const first = await page.request.post("/api/v1/auth/signup", {
    data: {
      name: "First Owner",
      email: `first-${suffix}@example.test`,
      password,
      company_name: `First workspace ${suffix}`,
    },
  });
  expect(first.status()).toBe(201);
  const leadResponse = await page.request.post("/api/v1/leads", {
    data: { name: "First workspace contact", company: "First company" },
  });
  expect(leadResponse.status()).toBe(201);
  const lead = await leadResponse.json();
  const conversion = await page.request.post(
    `/api/v1/leads/${lead.id}/convert`,
    { data: { create_deal: true, deal_name: privateDeal, amount: "1000" } },
  );
  expect(conversion.ok()).toBe(true);
  const otherContext = await browser.newContext();
  const secondEmail = `second-${suffix}@example.test`;
  const second = await otherContext.request.post(
    `${baseURL}/api/v1/auth/signup`,
    {
      data: {
        name: "Second Owner",
        email: secondEmail,
        password,
        company_name: `Second workspace ${suffix}`,
      },
    },
  );
  expect(second.status()).toBe(201);
  await otherContext.close();
  await page.goto("/dashboard");
  await expect(page.getByText(privateDeal, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
  let releaseResponse!: () => void;
  let requested!: () => void;
  const responseGate = new Promise<void>((resolve) => {
    releaseResponse = resolve;
  });
  const requestStarted = new Promise<void>((resolve) => {
    requested = resolve;
  });
  // Delay the real new-account response; its payload still comes from the actual backend.
  await page.route("**/api/v1/dashboard", async (route) => {
    requested();
    const response = await route.fetch();
    await responseGate;
    await route.fulfill({ response });
  });
  try {
    await page.getByLabel("Work email", { exact: true }).fill(secondEmail);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await requestStarted;
    await expect(
      page.getByRole("heading", { name: /Good .+, Second\./ }),
    ).toBeVisible();
    await expect(page.getByText(privateDeal, { exact: true })).toHaveCount(0);
  } finally {
    releaseResponse();
  }
  await expect(
    page.getByText("Your first opportunity is a good place to start.", {
      exact: false,
    }),
  ).toBeVisible();
});
