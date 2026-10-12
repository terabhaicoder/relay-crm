---
name: Relay CRM
description: A calm B2B sales desk with the legibility of a commercial ledger.
colors:
  forest: "#163e30"
  forest-dark: "#123025"
  leaf: "#dae6d3"
  orange: "#b66a28"
  canvas: "#f7f8f5"
  surface: "#ffffff"
  ink: "#24372e"
  muted: "#58685e"
  border: "#e4e8e1"
  secondary-text: "#63725d"
  focus: "#416d49"
  placeholder: "#61715e"
typography:
  display:
    fontFamily: 'Georgia, "Times New Roman", serif'
    fontSize: "38px"
    fontWeight: 400
    lineHeight: 1.18
    letterSpacing: "-1.2px"
  title:
    fontFamily: "Arial, Helvetica, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    letterSpacing: "-0.25px"
  body:
    fontFamily: "Arial, Helvetica, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Arial, Helvetica, sans-serif"
    fontSize: "13px"
    fontWeight: 500
rounded:
  chip: "5px"
  control: "7px"
  panel: "11px"
  radius: "12px"
spacing:
  control-gap: "8px"
  navigation-gap: "12px"
  panel-inset: "24px"
components:
  button-primary:
    backgroundColor: "{colors.forest}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  button-secondary:
    backgroundColor: "#edf3e8"
    textColor: "#254f36"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  button-subtle:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  navigation:
    backgroundColor: "{colors.forest-dark}"
    textColor: "#afc2b5"
    rounded: "{rounded.control}"
    padding: "10px 14px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
  status-chip:
    backgroundColor: "#f0f2ed"
    textColor: "#74816d"
    rounded: "{rounded.chip}"
    padding: "4px 7px"
---

# Design System: Relay CRM

## Overview

**Creative North Star: "The Sales Ledger"**

A B2B sales desk with the legibility of a commercial ledger. Dark evergreen navigation frames a warm off-white workspace; tables, customer context, and task queues carry the work. The user confirmed B2B sales and support and delegated visual execution; this direction is an implementation decision, not a claim of user-selected colors.

Georgia headings bring a quieter editorial voice to compact local sans-serif controls. Restrained borders separate working surfaces; shadows distinguish temporary overlays. Typography uses available local/system faces so no external font download blocks a hackathon demonstration.

**Key Characteristics:**
- Evergreen navigation and warm off-white working surfaces.
- Table-led workflows with compact controls and visible record context.
- Georgia page headings, local sans-serif body text, and tabular financial numerals.

### Evidence and provenance

Extracted from `frontend/src/app/globals.css` and sampled React controls. Frontmatter records the shipped CSS, including the final cascade overrides; the stylesheet remains the implementation source of truth. No computed browser styles were available. Sidecar tonal ramps are synthesized reference swatches, not additional shipped colors.

The initial concept tool ran in degraded mode because its online catalog was unreachable. There is no approved image comp. Browser visual review is currently blocked by local server binding restrictions; build/static checks must not be presented as screenshot verification.

### Review evidence

Independent static review checked record links, conversion locking, imports, notifications, binary file transport and automation payloads. The mechanical detector reported only the system Arial font as common; this remains intentional for reliable offline rendering, paired with Georgia headings. Neither review establishes visual or browser acceptance. The overlapping-dialog focus issue was fixed by binding keyboard handling to the topmost dialog; live keyboard verification remains pending.

## Colors

Evergreen and pale leaf tones anchor the palette; warm neutral surfaces keep dense records legible.

### Primary
- **Forest:** primary actions and caret color.
- **Deep forest:** persistent navigation and the authentication story surface.
- **Pale leaf:** supporting green accents.

### Secondary
- **Amber:** restrained attention color; duplicate warnings use a related warm tint.

### Neutral
- **Canvas / surface:** off-white workspace and white record surfaces.
- **Ink / muted / secondary text:** main text and the final cascade's supporting text colors.
- **Border:** quiet panel and table separation.
- **Focus / placeholder:** final authored input and keyboard-focus colors.

**The Source Truth Rule.** Describe shipped values and explicit provider states; never invent success metrics or configuration claims.

## Typography

**Display Font:** Georgia with Times New Roman and serif fallbacks.
**Body Font:** Arial with Helvetica and sans-serif fallbacks.

Page headings use the frontmatter display role; section headings use the title role. Body copy uses the body role, labels use the label role, table values use compact text (12px), and table headers use smaller text (11px). Phone page headings reduce to 31px. Existing 9–10px supporting text is recorded as implementation density, not a recommended minimum for new content.

**The Numerals Rule.** Financial figures use tabular numerals so values remain easy to compare.

## Layout

The desktop shell uses a fixed sidebar (228px) and a workspace content maximum (1680px), with content padding (40px 38px 32px). The dashboard pairs pipeline and tasks in a 1.25:1 grid with a 22px gap. Searchable tables scroll horizontally, and pagination remains visible below results. Forms use two columns until the phone breakpoint; the record drawer is 540px wide, capped at the viewport width.

At 1180px and below the sidebar narrows to 205px and dashboard columns stack. At 780px and below navigation becomes a sliding drawer, content padding reduces to 29px 20px 22px, forms become one column, and the summary strip becomes two columns. At 1600px and above the layout increases breathing room. These are authored rules; rendered behavior remains unverified.

## Elevation & Depth

Ordinary panels use borders without shadows. Floating search, notification, and feedback surfaces use the shared soft shadow; the record drawer has a separate directional shadow. Selection, caret, scrollbars, and focus rings are themed.

- **Floating surface:** `0 20px 65px #163e301a`.
- **Record drawer:** `-15px 0 60px #13291b17`.

**The Working Surface Rule.** Keep ordinary record surfaces flat; reserve soft elevation for temporary overlays.

Buttons transition background and color over 0.16s with ease. The mobile navigation uses a 0.2s transform transition. Reduced-motion preferences disable animation and transitions.

## Shapes

Controls have gently rounded corners; panels use slightly larger corners and badges tighter corners, as recorded in frontmatter. The shared radius variable exists alongside these specific component values. Borders are thin and neutral. Authored SVG icons share a consistent stroke; initials identify people and companies.

## Components

### Buttons
Compact, restrained controls with primary forest, secondary pale green, and subtle bordered variants. Minimum height is 39px. Primary hover darkens to the shipped green hover tone; disabled controls reduce opacity and use a not-allowed cursor. Focus uses a 3px outline with a 3px offset.

### Inputs / Fields
White fields with a thin neutral border, labelled controls, and a minimum height of 42px. Errors sit beside the relevant form. Mobile editor inputs use 16px text. Clearing optional relations and dates has explicit empty-state semantics.

### Navigation
Dark evergreen with muted green labels. Hover brightens the label; active navigation uses a pale leaf fill and darker green text. Compact phone navigation retains the same destinations.

### Chips
Small rectangular status tags use semantic green, neutral, and amber families. The sidecar captures the current neutral badge; its small type and contrast require live accessibility review and are not endorsed as defaults for new surfaces.

### Cards / Containers
White panels use a single thin border and compact heading insets (23px 24px 20px). Tables and task lists are primary content, while deal cards support stage movement. Native confirmation dialogs remain limited exceptions for destructive actions.

## Do's and Don'ts

### Do:
- Do retain labelled inputs, visible focus, and reduced-motion behavior.
- Do use tabular numerals and Indian currency formatting for financial summaries.
- Do keep fictional sample records and unconnected provider states explicit.

### Don't:
- Don't present static inspection or compilation as browser acceptance.
- Don't replace record tables and task queues with decorative cards.
- Don't make emoji or native browser dialogs the main interaction language; current delete and merge confirmations are implementation exceptions.

### Current audit evidence — 2026-10-12

Real desktop screenshots now live in `artifacts/crm-audit`: import result and populated table, task drawer/custom dropdown, and full landing. The palette and layout identity were retained. Paise no longer disappear, timestamps state IST, and owner avatars no longer imply the current viewer owns someone else's deal. Native date submission, relationship clearing, assignment and loading/retry states received functional repairs. Earlier references to no browser evidence describe prior sessions. This session's requested mobile viewport did not apply (measured1792×976); the new screenshots are explicitly desktop and do not certify mobile accessibility.
