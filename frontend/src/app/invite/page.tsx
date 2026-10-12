import { Suspense } from "react";
import type { Metadata } from "next";
import { InvitationAcceptance } from "@/components/account-access";
export const metadata: Metadata = {
  title: "Join your workspace · Relay",
  referrer: "no-referrer",
  robots: { index: false, follow: false },
};
export default function InvitePage() {
  return (
    <Suspense
      fallback={
        <main className="loading-screen">Checking your invitation…</main>
      }
    >
      <InvitationAcceptance />
    </Suspense>
  );
}
