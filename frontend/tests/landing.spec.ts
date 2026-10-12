import { expect, test } from "@playwright/test";

test("public homepage describes the product and links to real workspace entry points", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    /Good relationships\s*deserve a great relay\./,
  );
  await expect(page.getByRole("navigation", { name: "Website navigation", exact: true })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Main navigation", exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Work email", { exact: true })).toHaveCount(0);

  for (const name of ["Get started", "Bring your team together", "Get started with Relay"]) {
    await expect(page.getByRole("link", { name, exact: true })).toHaveAttribute("href", "/dashboard?signup=1");
  }
  for (const name of ["Sign in", "Explore your workspace", "Open workspace"]) {
    await expect(page.getByRole("link", { name, exact: true })).toHaveAttribute("href", "/dashboard");
  }
  await expect(page.getByRole("link", { name: "See how it connects", exact: true })).toHaveAttribute("href", "#workflow");
  await expect(page.getByRole("tabpanel")).toContainText(
    "Workflow illustration. Your workspace starts with your own data.",
  );

  await page.getByRole("link", { name: "Get started", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard\?signup=1$/);
  await expect(page.getByRole("heading", { name: "Start your next chapter.", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create workspace", exact: true })).toBeVisible();
});

test("journey tabs work from the keyboard and FAQ answers expand honestly", async ({ page }) => {
  await page.goto("/");
  const tabs = page.getByRole("tablist", { name: "Customer journey stages", exact: true });
  const lead = tabs.getByRole("tab", { name: /^Meet your next customer\./ });
  const deal = tabs.getByRole("tab", { name: /^Give every deal a next step\./ });
  const support = tabs.getByRole("tab", { name: /^Make the handoff feel seamless\./ });
  const panel = page.getByRole("tabpanel");
  await expect(lead).toHaveAttribute("aria-selected", "true");
  await lead.focus();
  await lead.press("ArrowRight");
  await expect(deal).toBeFocused();
  await expect(deal).toHaveAttribute("aria-selected", "true");
  await expect(lead).toHaveAttribute("tabindex", "-1");
  await expect(panel).toHaveAttribute("aria-labelledby", await deal.getAttribute("id") as string);
  await expect(panel.getByRole("heading", { level: 3 })).toHaveText("The whole conversation travels with you.");
  await deal.press("End");
  await expect(support).toBeFocused();
  await expect(panel.getByRole("heading", { level: 3 })).toHaveText("A new team. The same customer story.");
  await support.press("ArrowRight");
  await expect(lead).toBeFocused();
  await lead.press("End");
  await support.press("Home");
  await expect(lead).toBeFocused();
  await expect(tabs.getByRole("tab", { selected: true })).toHaveCount(1);

  const question = "Does Relay send email or connect to Gmail?";
  const answer = page.locator("details").filter({ has: page.locator("summary", { hasText: question }) });
  const summary = answer.locator("summary");
  await expect(answer).toHaveJSProperty("open", false);
  await summary.click();
  await expect(answer).toHaveJSProperty("open", true);
  await expect(answer.locator("p")).toBeVisible();
  await expect(answer.locator("p")).toContainText("Gmail connection and sending are not enabled in this release");
  await summary.focus();
  await summary.press("Enter");
  await expect(answer).toHaveJSProperty("open", false);
  await expect(answer.locator("p")).toBeHidden();
});

test("mobile homepage menu navigates and the layout does not overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const menu = page.getByRole("button", { name: "Open navigation", exact: true });
  await expect(menu).toBeVisible();
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await menu.click();
  const mobileNavigation = page.getByRole("navigation", { name: "Mobile website navigation", exact: true });
  await expect(mobileNavigation).toBeVisible();
  await expect(page.getByRole("button", { name: "Close navigation", exact: true })).toHaveAttribute("aria-expanded", "true");
  await expect(mobileNavigation.getByRole("link", { name: "Sign in to Relay", exact: true })).toHaveAttribute("href", "/dashboard");
  await mobileNavigation.getByRole("link", { name: "Your workspace", exact: true }).click();
  await expect(page).toHaveURL(/\/#features$/);
  await expect(mobileNavigation).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Open navigation", exact: true })).toHaveAttribute("aria-expanded", "false");
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});
