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

1. Primary data source: session-key endpoint (covers app + Code usage) vs local JSONL only (zero credentials, Code-only accuracy) vs both.
2. Keeper default schedule anchor (e.g. 07:00 local) and model (sonnet as requested vs haiku to minimize burn).
3. Whether the discharged cloud should also show the weekly cap or only the 5h window.

## Session log

- 2026-07-10 — STEP 0: scaffolded the control layer (4 files). No feature code written. Next: verify the usage endpoint per G7 and get owner decision #1 before writing the fetcher.

## Notes / blockers

- G7: usage endpoint is unverified — `FACTS.md` carries a [VERIFY] placeholder. Do not write the remote fetcher until verified or Pier decides JSONL-only.
