import { PublicLeadForm } from "@/components/lead-capture";

export default async function CapturePage({ params }: { params: Promise<{formId:string}> }) {
  const {formId} = await params;
  return <PublicLeadForm key={formId} formId={formId}/>;
}
