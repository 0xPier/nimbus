# PROGRESS.md — Nimbus build state

Rules: read this file at the start of every session. Update it **only after a done-when check passes**. Pier's manual edits to this file always win.

## Current phase

**P1 — Data layer** (not started). STEP 0 (control-layer scaffold) complete.

## Phase checklist

- [x] STEP 0 — Control layer scaffolded (CLAUDE.md, FACTS.md, PROGRESS.md, BUILD_PHASES.md)
- [ ] P1 — Data layer (blocked on: G7 endpoint verification + owner decision #1)
- [ ] P2 — Cloud in the menu bar
- [ ] P3 — Notifications
- [ ] P4 — Window keeper (opt-in)
- [ ] P5 — Ship

## Open owner decisions (park here, don't guess — Pier decides)

*(none currently open)*

## Decided by Pier (2026-07-10)

1. **Data source: both** — session-key endpoint primary, local JSONL fallback.
2. **Keeper: haiku model.** Schedule anchor is **read from the actual observed reset time**, with a settings field letting the user override/input it manually.
3. **Discharged cloud shows both** the 5h window and the 7-day cap.

## Session log

- 2026-07-10 — STEP 0: scaffolded the control layer (4 files). No feature code written.
- 2026-07-10 — Pier decided all 3 open decisions (see "Decided by Pier"). G7 verification complete: usage endpoint, auth, and response schema recorded in FACTS.md with source links. P1 is unblocked.

## Notes / blockers

- Endpoint is internal/undocumented (see FACTS.md caveat) — fetcher must degrade to JSONL + honest disconnected state (G6) on any failure.
