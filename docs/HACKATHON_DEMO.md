# A five-minute Relay CRM demonstration

The story: a B2B buyer arrives, sales follows up, the opportunity closes, and support receives the same customer context. Show actions and their resulting records rather than reading a feature list.

## Before presenting

1. Start `python3 scripts/dev.py` from the project root and open http://127.0.0.1:3007.
2. Create a workspace with your own email and password. Use the explicit sample-data action if you want a populated workspace. Explain that all sample records are fictional.
3. Walk through the sequence below once on your presentation machine. Browser acceptance could not run inside the development sandbox, so this rehearsal is necessary.
4. Keep an empty second workspace available to demonstrate isolation and a clean starting experience. Use separate browser profiles or sign out before switching.

## The story

**Start with the overview.** “This is what the team should work on today.” Point to database-backed pipeline totals and the follow-up queue. Open one of the associated record lists.

**Capture an inquiry.** Add a fictional lead such as “Ananya Rao — Example Distribution.” Give it a fictional email at `example.com`, a source and estimated value. Create a follow-up task linked to the lead. Show that the task remains after leaving and reopening the page.

**Automate the routine work.** Create a rule for a new lead with source Website: create a task named `Call {{name}}`. Add a second fictional Website lead. Show its real task, notification and execution log. Explain that actions are conditional and retries are deduplicated.

**Convert without losing context.** Convert the first lead. Open its linked company, contact and deal. Reopening the converted lead should show the same references, not new duplicate records.

**Progress and close the deal.** Move the deal to another pipeline stage and show its history. Mark it won. Return to the overview: it belongs in won revenue and no longer contributes to the open pipeline. Alternatively mark a deal lost and demonstrate that a reason is required.

**Hand off to support.** Create a ticket linked to the same company/contact/deal. Add an internal note, save a customer reply draft and resolve the ticket. Internal collaboration and unsent customer drafts are clearly distinguished.

**Finish with trust and portability.** Show CSV import validation/error download, record export, member roles and the ability to sign out. If asked about Gmail, show its actual disconnected status: the next integration step is OAuth and provider-confirmed sending/sync, not a fabricated delivery result.

## A concise closing line

“Relay keeps the customer context connected from first inquiry through the sales result and support follow-up. Every change you saw was saved by the backend.”

Do not claim production certifications, unmeasured performance, paying customers, live Gmail delivery, or the entire future ERP roadmap. The strongest evidence is a coherent, repeatable workflow.
