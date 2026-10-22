# A local Relay CRM demonstration

The story: a B2B inquiry becomes a connected customer, a commercial quotation records the sales agreement, and follow-ups/support retain the same context. Show each action and its resulting saved record.

## Before presenting

1. Start `python3 scripts/dev.py` from the project root and open http://127.0.0.1:3007 in Chrome. For an existing installation, restart the local API to apply numbered migrations `0006` through `0010` and load the new routes.
2. Sign up for a disposable demonstration workspace. Use fictional names and an `example.test` address. The optional sample-data action is explicit and its records are fictional.
3. Rehearse the sequence manually in Chrome on the presentation machine. This is a local prototype demonstration; it does not certify Docker, remote deployment or production readiness.
4. Keep a separate empty workspace available if you intend to demonstrate isolation. Use separate browser profiles or sign out when switching; do not overwrite an existing user's records.

No external provider credentials or new runtime dependency are required for these local features. Supplying Gmail credentials alone would not implement the missing mailbox/sending adapter.

## Current observed path

The 22 October manual Chrome review verified signup → lead → linked company/contact/deal conversion → quotation create/issue/record acceptance with the deal marked won → forecast showing **₹1,25,000.50**. It also verified company overview → pre-linked dated follow-up → correct My Day and Calendar entries.

Additional manual Chrome checks verified contact → prefilled email draft → save/reopen with contact retained → template name/company/email substitution → save; and company-linked support ticket → internal note → Resolved status saved and visible in the list.

The earlier private saved-view lifecycle was verified, but its full-width list bar was subsequently removed at the user's request. Existing presets and their API remain stored; saved views are no longer exposed in the current list UI and should not be included in the demonstration. Search, filters, sorting and pipeline controls remain available.

Campaign review created a campaign with ₹5,000.50 budget, added the existing converted Mira lead, observed one member with 1/1 converted and 100%, then removed membership and confirmed the original lead stayed unchanged. This checks pre-converted membership, not conversion while enrolled.

Automation review created a leads.created rule with a one-day task, added Sam Fictional Inquiry and found “Review new customer inquiry” due 2026-10-23. Its record retained the Sam lead link and automation note; completing it persisted completed status in My Tasks. The later Chrome review verified local form submission → assigned lead → immediate task → one-minute delayed in-app notification, compatible Buying priority value → converted contact, and a repeat inquiry after conversion → two inquiry receipts linked to one lead. Execution results remained available after the API restart. Rehearse the segments below on the presentation machine, and use [CHECKLIST.md](../CHECKLIST.md) for their exact observed scope.

## New local acquisition and automation story

1. Settings → Lead capture → Create lead form. Choose the source and assignment rotation; open the local form link.
2. Automations → New workflow. Use Lead created, a task named “Call {{name}}”, followed by an in-app notification with a one-minute delay.
3. Submit a fictional inquiry through the form with contact consent. Inspect Leads and the form's inquiry list. Repeating the same email retains the existing lead and stores the new message.
4. Execution history shows the task's real record link, then the notification completes while the API runs. Open the notification bell to see the message.
5. Settings → Custom fields: create matching text keys on Leads and Contacts. Save the lead value, convert, then show that value on the contact. This path was manually verified with Buying priority.
6. Continue with the quotation and support story below. External connector cards can be shown as planned; their detail buttons explain what is available locally.

The recorded audit used separate local ports and a temporary database containing only fictional records. Use the standard launcher defaults above for a new demonstration workspace.

## Main sales story

**Capture an inquiry.** Add a fictional lead such as “Ananya Rao — Example Distribution,” with an `example.test` email, source and estimated value. Open it again to show persistence.

**Convert without losing context.** Convert the lead and open its company, contact and deal links. The converted lead is retained; another conversion must not create duplicate customers or opportunities.

**Prepare the commercial proposal.** From the deal choose **Create quotation**. Enter the offer name, line descriptions, quantities/rates and any discount. Save and review the server-calculated total and customer context. For the verified example, use a total of ₹1,25,000.50. These are INR commercial estimates excluding tax, not invoices.

**Record the outcome.** Issue the quotation to lock its terms. Record customer acceptance with evidence/reference text and explicitly select the option to mark the linked deal won. Reopen both records to show the connected result. Explain that this records a decision entered by the user; it does not verify delivery, an electronic signature or payment. Print opens the saved document for the browser's print workflow.

**Read the forecast.** Open Reports and select the relevant date range/pipeline. Show the accepted deal under Won at ₹1,25,000.50 and its removal from open pipeline. Open deals use expected close dates; won/lost values use actual close dates in IST. Weighted forecast is an estimate. The overdue/undated attention lists cover open deals outside the selected date period too.

**Keep the next promise.** Open the company's Customer overview and choose **Add follow-up**. Enter a due date and save the pre-linked task. Confirm it appears in My Day and on the Calendar date, then reopen the record to show the retained company link.

## Additional connected segments to rehearse

- **Prepare a connected email.** Choose **Prepare email draft** from a customer record, apply a template, review the recipient and substituted name/email/company fields, and save. Reopen it from the record's linked draft list. Unresolved placeholders must be reviewed; the message remains unsent.
- **Automate a follow-up.** Reproduce the two-step local capture workflow above, or create a `leads.created` rule with action `create_task`, task text “Review new customer inquiry” and due in one day. Add a fictional lead, open the generated task to show its lead link/automation note, then complete it. Its due date follows the day of your demonstration; 2026-10-23 was the observed date during the 22 October review. Immediate task creation and a delayed in-app notification were manually verified; other triggers, condition permutations and failure/retry paths need their own rehearsal. Branching, recurring schedules and external message delivery are not implemented.
- **Review campaign membership.** Create a campaign, add a real lead/contact from the workspace, and inspect conversion counts. Removing membership must retain the original record. A converted-member count is not campaign-attributed revenue or ROI.
- **Hand off to support.** Create a ticket linked to the same company/contact/deal. Add an internal note, save an explicitly unsent customer reply draft, and resolve the ticket. Inbound support intake, delivered replies and SLA escalation are not implemented.
- **Show portability and access.** Demonstrate CSV validation/error downloads, filtered export, existing role controls and sign-out only when those segments have been rehearsed. Never treat historical checks as proof of a new presentation-machine run.

## Present the boundaries clearly

Relay now has local lead capture with consent validation, duplicate handling and round-robin assignment; connected sales and customer records; durable ordered automation; typed custom fields; quotations; and forecasting. Public forms are available in the local single-instance demo, not an externally hosted acquisition service. Live external communications/connectors, customer-originated support intake/SLA, branching or recurring automation, and advanced customization/reporting remain future work. Saved-view controls are not exposed in the current list UI. The [CRM audit](CRM_AUDIT_2026-10-22.md) records the researched comparison and next priorities.

Use the presentation label **Local working prototype · Fictional demo data**. Quotation acceptance records a user-entered decision, email/support replies remain unsent drafts, and weighted forecasts are estimates. Sample pipeline and won values demonstrate persisted records, not business traction or collected revenue.

Do not claim a complete automated E2E pass, production certification, unmeasured performance, real mail delivery, collected revenue or the future ERP roadmap. Demonstrate the changes actually persisted by the backend.
