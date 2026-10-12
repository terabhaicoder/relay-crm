import { notFound } from "next/navigation";

const workspaceSections = new Set([
  "dashboard", "workbench", "pipelines", "leads", "contacts", "accounts", "deals", "activities",
  "calendar", "campaigns", "tickets", "reports", "automations",
  "communications", "settings",
]);
export default async function Page({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  if (!workspaceSections.has(section)) notFound();
  // The root layout preserves the workspace shell between valid module routes.
  return null;
}
