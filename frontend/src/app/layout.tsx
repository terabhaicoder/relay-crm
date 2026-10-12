import type { Metadata } from "next";
import "./globals.css";
import { Suspense } from "react";
import { WorkspaceRouter } from "@/components/crm";

export const metadata: Metadata = {
  title: "Relay CRM",
  description: "Your people, your pipeline, and your next conversation.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en-IN"><body><Suspense fallback={<main className="loading-screen">Opening Relay…</main>}><WorkspaceRouter>{children}</WorkspaceRouter></Suspense></body></html>;
}
