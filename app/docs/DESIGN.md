---
version: alpha
name: "DebateAI"
description: "A compact local-first meeting control desk that turns live speech into calm, actionable guidance."
colors:
  primary: "#0D9488"
  accent-dark: "#0F766E"
  accent-light: "#2DD4BF"
  evidence: "#F59E0B"
  canvas-light: "#F1F5F9"
  surface-light: "#FFFFFF"
  text-light: "#0F172A"
  canvas-dark: "#0F172A"
  surface-dark: "#1E293B"
  text-dark: "#F1F5F9"
  danger: "#EF4444"
typography:
  display:
    fontFamily: "Inter Variable, Inter, system-ui, -apple-system, Segoe UI, sans-serif"
  body:
    fontFamily: "Inter Variable, Inter, system-ui, -apple-system, Segoe UI, sans-serif"
  utility:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, Liberation Mono, monospace"
rounded:
  sm: "0.25rem"
  md: "0.375rem"
  lg: "0.5rem"
  xl: "0.75rem"
spacing:
  compact-gap: "0.5rem"
  panel-gap: "0.75rem"
  page-gutter: "1rem"
  page-gutter-wide: "1.5rem"
components:
  live-panel:
    rounded: "0.75rem"
    backgroundColor: "#FFFFFF"
  insight-card:
    rounded: "0.5rem"
    backgroundColor: "#FFFFFF"
  focus-ring:
    width: "2px"
---

# DebateAI Design System

## Overview

### Creative North Star

DebateAI should feel like a well-run broadcast control desk reduced to the essentials: live signals are visible at a glance, evidence is traceable, and the operator can keep listening instead of managing the interface.

### Product context and register

- **Audience and primary job:** A person actively participating in a meeting who needs transcript context and useful next moves without losing the conversational thread.
- **Target markets and evidence:** The product is general-purpose and self-hosted; the repository and product documentation do not constrain it to a single market.
- **Locales and language policy:** The established interface is English. Task-specific live guidance may use the configured meeting language; the German Debate Copilot intentionally presents its speaking moves in German.
- **Usage scene:** Laptop or desktop during a live call, under time pressure, with high information density and frequent updates.
- **Register:** Product. Clarity, stable geometry, and low interruption outrank decorative expression.
- **Memorable signature:** A live “speaking track” groups direct answer, counterargument, and counter-question as three parallel moves linked to one target claim.
- **Restraint:** Transcript, recording controls, errors, privacy state, and ordinary insights retain familiar DebateAI patterns and must not be visually displaced by the speaking track.
- **Anti-references:** Not a sales dashboard full of KPI gradients; not a chatbot transcript; not a newsroom-style decorative layout. Those registers compete with the real conversation.
- **Token ownership/runtime mapping:** The mature runtime token spine in `frontend/src/index.css` is canonical. `frontend/tailwind.config.js` adapts semantic CSS variables for components; this file mirrors accepted values and rationale rather than generating code.

## Colors

Teal is the live/active signal and focus color. Amber marks evidence, caution, and unverified facts. Slate surfaces create depth without decorative gradients. Red is reserved for actual failure or destructive action. Light and dark modes remap semantic variables in `frontend/src/index.css`; components consume semantic Tailwind names rather than raw values. Color never carries state alone.

## Typography

Inter Variable is the existing display and body family. It keeps live guidance compact and readable at small sizes. Monospace utility labels are reserved for short categories, statuses, and technical metadata; they never carry paragraph copy. Sentence case is preferred for actions and messages; uppercase is limited to small scan labels with deliberate tracking.

## Layout

The active-call screen has one vertical scroll owner per column. Time-critical guidance sits above the ordinary insight feed but stays compact; it must not alter transcript scrolling. The standard rhythm is 0.5rem within compact groups, 0.75rem between panels, and 1rem/1.5rem page gutters. Responsive layouts reflow the three speaking moves from columns to stacked cards without hiding content.

## Elevation & Depth

Hierarchy comes primarily from tonal surfaces and one-pixel borders. A restrained small shadow may lift a live panel from the canvas; static nested cards stay flat. Dark mode uses authored surfaces, not inversion. Loading and status changes reserve their geometry to avoid jumps.

## Shapes

Controls and nested cards use 0.375rem to 0.5rem radii. Major live panels may use 0.75rem. Pills are reserved for compact statuses and confidence labels, not general containers. Dividers are one-pixel semantic borders.

## Components

### Foundational visual states

Interactive controls provide visible hover, focus-visible, active, disabled, and busy states. Focus uses the global two-pixel semantic ring. Background work preserves readable content and labels uncertainty; errors remain inline with a recovery path. Loading uses the app-owned indeterminate spinner in a stable region. Skeletons are not a default DebateAI pattern.

### Buttons and actions

Safe primary actions use solid teal. Secondary actions use neutral outline or ghost treatment. Warning uses amber, and irreversible danger uses red with spatial separation. Icon-only controls need an accessible name; enabled actions use a pointer cursor and keep stable dimensions while busy.

### Navigation and data display

The shell, active-call columns, insight lists, and transcript keep their established owners. Cards wrap important text; only preview text may be line-clamped. External evidence links are explicit links with an external-link mark and safe new-tab behavior.

### Forms and overlays

Existing shared confirmation, status, and field patterns remain canonical. Errors explain recovery without exposing raw backend internals. Browser-native alert, confirm, and prompt dialogs are not product UI.

### Iconography

Lucide is the canonical icon family, using 1.5–2px strokes and 12–20px sizes in dense surfaces. Icons supplement labels and do not replace unfamiliar actions or statuses.

### Motion

Motion communicates live activity or a newly available result. Routine transitions stay around 120–200ms and use opacity or small positional changes. Continuous rotation is limited to active loading indicators. `prefers-reduced-motion` removes transforms and rotation.

### Content and data visualization

Copy is direct, operational, and honest about uncertainty. Recommendations use spoken language; metadata uses concise labels. Evidence always names the claim it supports. Timestamps distinguish freshness from durability and do not imply a result was persisted.

## Do's and Don'ts

- **Do:** Keep the next useful spoken move visible without hiding the ordinary insight history.
- **Do:** Connect every external source to the exact claim it checks and label unverified guidance in text.
- **Don't:** Add decorative gradients, glass effects, or dashboard metrics to a live conversation surface.
- **Don't:** Let loading, research, or long localized content shift controls or create an inaccessible nested scroll region.
