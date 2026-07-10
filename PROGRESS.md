# PROGRESS.md — Nimbus build state

Rules: read this file at the start of every session. Update it **only after a done-when check passes**. Pier's manual edits to this file always win.

## Current phase

**P1 — Data layer** (not started). STEP 0 (control-layer scaffold) complete.

## Phase checklist

- [x] STEP 0 — Control layer scaffolded (CLAUDE.md, FACTS.md, PROGRESS.md, BUILD_PHASES.md)
- [x] P1 — Data layer — **done-when PASSED 2026-07-10**: after Pier's fresh CLI login, `python -m nimbus.status` printed live % + reset for both windows via OAuth (5h: 42% used, resets 18:00; 7d: 16% used, resets Sat 14:00); disconnected + JSONL fallback paths verified earlier.
- [ ] P2 — Cloud in the menu bar — built; 10s debug smoke test clean, state mapping unit-verified (6/6 states). **Awaiting Pier's visual confirmation of `--debug` cycling.**
- [x] P3 — Notifications — reset detector fires exactly once across repeated polls (simulated, 8 polls → 1 event) and a real notification was sent end-to-end via osascript.
- [ ] P4 — Window keeper — built; stub-CLI test shows exactly 1 call with correct argv (`-p "Reply with exactly: ok" --model haiku`), off-by-default enforced. **Full done-when needs a real reset event with toggle on/off.**
- [ ] P5 — Ship — install.sh ran: LaunchAgent loaded and app running. README privacy section done. **Reboot-survival and uninstall not yet exercised.**

## Open owner decisions (park here, don't guess — Pier decides)

*(none currently open)*

## Decided by Pier (2026-07-10)

1. **Data source: both** — session-key endpoint primary, local JSONL fallback.
2. **Keeper: haiku model.** Schedule anchor is **read from the actual observed reset time**, with a settings field letting the user override/input it manually.
3. **Discharged cloud shows both** the 5h window and the 7-day cap.
4. **OAuth refresh: Pier refreshes it himself** by using claude normally — Nimbus stays strictly read-only (G2), never touches Claude Code's Keychain item.

## Session log

- 2026-07-10 — STEP 0: scaffolded the control layer (4 files). No feature code written.
- 2026-07-10 — Pier decided all 3 open decisions (see "Decided by Pier"). G7 verification complete: usage endpoint, auth, and response schema recorded in FACTS.md with source links. P1 is unblocked.
- 2026-07-10 — P1 built: `nimbus/` package (models, config+Keychain, api fetcher, jsonl fallback, status CLI). Verified: JSONL fallback derives the live window from real logs (opened 13:08 → resets 18:08, utilization honestly unknown); simulated network cut with key → clean JSONL fallback; no key + no JSONL → `disconnected` (exit 2). **Not yet verified: live API % (needs Pier's sessionKey via `python -m nimbus.status --set-key`). P1 done-when therefore NOT passed — box stays unchecked.**

- 2026-07-10 — UI rework per Pier: no dock icon (accessory activation policy); menu bar icon is now a *drawn* cloud (orange charge that drains to grey as usage is used, bolt when discharged, green bolt recharging, red slash disconnected) + remaining % text; new movable desktop pet widget (borderless floating panel, drag anywhere, position remembered, gentle bob animation, % + countdown) toggled via "Show desktop cloud (pet)". Icon renders verified visually across all states.

## Notes / blockers

- Endpoint is internal/undocumented (see FACTS.md caveat) — fetcher must degrade to JSONL + honest disconnected state (G6) on any failure.
