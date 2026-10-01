---
name: desktop-workspace-ui
description: Rules for the Tauri desktop shell, harness launch and reconnect, the renderer, the nine-stage work trail, ledger projections, accessibility and visual direction on macOS and Linux. Use when touching desktop/ or any view of ledger state.
---

# Desktop workspace UI

**Read first:** `../desktop_experience.md`; `../gui_workflow.md` ("Workspace layout", "Stages and evidence",
"Event projection and intervention"); D19, D24; scenarios A31, A34, A44; controls C17, C23.

## Shell and harness

- Tauri 2.12.0. Keep Rust minimal: launch or reconnect to the harness sidecar, native menu, folder picker,
  window lifecycle. All business logic is in the Python harness.
- One harness per user profile: instance lock + authenticated handshake; loopback only, short-lived app
  credential, strict Origin/Host checks, no permissive CORS.
- The renderer talks **only** to the harness. It cannot spawn processes, read arbitrary files, evaluate
  returned code or load remote content. Tauri capabilities are the narrowest that work.
- Reports, notebooks and imported docs render in a separate inert viewer: no scripts, no IPC, no network.
  Never an untrusted iframe in the privileged window.
- The folder picker returns an opaque scoped handle. The model API key never reaches renderer code.
- Lifecycle: closing the window detaches observation; with active jobs the default is pause-then-quit (D24).
  Reopen reconnects and replays the ledger; never restart jobs from UI assumptions. Sleep or harness crash →
  leases expire → reconcile before new dispatch.
- The workspace opens **before** any model loads; controls and manual setup work with the assistant absent.

## Views are projections

A reducer derives display state from ledger events and dependency validity. The model cannot emit a
completed stage. Stage IDs, in order: `goal`, `environment`, `data`, `plan`, `develop`, `self_check`,
`evaluate`, `report_release`, `operate`. Display states: `pending`, `running`, `waiting_for_user`,
`pause_requested`, `paused`, `failed`, `inconclusive`, `completed`, `skipped`, `stale`. Show completion and
outcome separately: a completed evaluation can be FAIL. Skipped needs a reason and is forbidden for a
mandatory gate. Hardware and availability displays go stale after 60 s (D19). Lost stream →
"Connection lost; last known state…".

## Layout

Header (workload, revision, status, compute, budget, Pause/Cancel) · left work trail · main canvas (activity,
plan diff, code, relationship map with a table equivalent, report) · contextual evidence margin · persistent
composer at the bottom · output shelf with "Open output folder" · fixed resource status. Pause and Cancel sit
outside the composer and are also native menu items with keyboard shortcuts.

## Visual direction

Quiet editorial canvas: generous whitespace, clear type, thin rules, evidence opening beside the item it
explains. No grid of boxed cards, no ornamental motion, no colour-only status, no hover-only information, no
invented progress percentages, no "thinking" panel. Tables and code stay rectangular.

## Accessibility

Keyboard reaches every control, including the work trail and the relationship list; visible focus; focus
returns after a decision; text plus icon for state; reduced-motion respected; screen-reader announcements
for state changes; stable scroll while activity arrives.

## Tests

Renderer: Vitest for the reducer (duplicate, out-of-order and replayed events; spoofed completion prose),
Playwright + axe against the real harness. Desktop: tauri-driver end-to-end on Linux under a virtual display;
on macOS a scripted launch → handshake → quit smoke test, with the gap stated. Lifecycle: close, quit, crash,
reopen, second instance.

## Avoid

State kept only in the browser; a control that works on one OS; OS-specific code outside the shell adapter;
a drag-and-drop pipeline designer or general IDE.
