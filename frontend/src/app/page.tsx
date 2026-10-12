import type { Metadata } from "next";
import { Landing } from "@/components/landing/landing";

export const metadata: Metadata = {
  title: "Relay — Sales and support, in good company",
  description: "Bring B2B sales and customer support together. Manage leads, contacts, companies, deals and customer conversations in one connected Relay workspace.",
};

export default function Page() {
  return <Landing />;
}
