# Relay CRM

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The user is preparing an end-to-end CRM for a hackathon demonstration and wants it usable as a real system. Confirmed focus: B2B sales plus customer support. Primary users are sales representatives, a sales manager/owner and support agents.

## Product Purpose

Manage a customer relationship from first inquiry through qualification, follow-up, deal progression and customer support. Success means users can perform and revisit these actions against a persistent backend, with convincing visual quality and no disconnected demo screens.

## Operating Context

Desktop-first daily sales work with responsive access on phones. Demonstration data is explicitly fictional and opt-in. Actual empty workspaces must also work. ProcessPay and established CRM products are reference material; the user explicitly said neither reference nor the initial ERP specification is a fixed source of truth.

## Capabilities and Constraints

Current implementation priorities: secure workspaces; leads; contacts; organizations; pipeline and deal history; tasks and notes; campaigns; support tickets; reports; search; imports and exports; settings. Integration status must reflect real provider configuration and responses. Gmail is a confirmed future connection; the user explicitly deferred connecting it. The original full ERP, payroll, GST and manufacturing list is a future roadmap rather than this CRM's immediate promise. The deadline remains unanswered.

The local environment has restricted package downloads and Docker socket access. A real file-backed SQLite database is an acceptable single-instance development/demonstration deployment choice; broader deployment and PostgreSQL validation remain separate deliverables.

## Evidence on Hand

ProcessPay source exists locally and in the connected AugustInnovate GitHub repositories. No customer testimonials, commercial usage figures, provider credentials or performance benchmarks have been supplied.

## Product Principles

- Every actionable control completes a real workflow or gives a clear recoverable error.
- Follow-up and context should be visible at the point of action.
- Preserve relationship history across conversion and closing.
- Financial summaries and counts come from the database.
- Make fictional demonstration data visibly distinct from real workspaces.

## Accessibility & Inclusion

Keyboard navigation, visible focus, labelled inputs, readable contrast, mobile layouts and simple English are required. Use Indian currency formatting for the initial market while storing exact decimal amounts.
