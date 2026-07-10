# PROGRESS.md — Nimbus build state

Rules: read this file at the start of every session. Update it **only after a done-when check passes**. Pier's manual edits to this file always win.

## Current phase

**P1 — Data layer** (not started). STEP 0 (control-layer scaffold) complete.

## Phase checklist

- [x] STEP 0 — Control layer scaffolded (CLAUDE.md, FACTS.md, PROGRESS.md, BUILD_PHASES.md)
- [ ] P1 — Data layer — built; JSONL/disconnected paths verified. **Blocked on live %: Claude Code OAuth token in Keychain expired 2026-05-31 (endpoint returns 401). Waiting on Pier: refresh via a claude run, or paste sessionKey.**
- [ ] P2 — Cloud in the menu bar — built; 10s debug smoke test clean, state mapping unit-verified (6/6 states). **Awaiting Pier's visual confirmation of `--debug` cycling.**
- [x] P3 — Notifications — reset detector fires exactly once across repeated polls (simulated, 8 polls → 1 event) and a real notification was sent end-to-end via osascript.
- [ ] P4 — Window keeper — built; stub-CLI test shows exactly 1 call with correct argv (`-p "Reply with exactly: ok" --model haiku`), off-by-default enforced. **Full done-when needs a real reset event with toggle on/off.**
- [ ] P5 — Ship — install.sh ran: LaunchAgent loaded and app running. README privacy section done. **Reboot-survival and uninstall not yet exercised.**

## Open owner decisions (park here, don't guess — Pier decides)

4. OAuth token refresh: the Claude Code Keychain token is expired. Should Nimbus (a) rely on Pier refreshing it by using claude normally [recommended — keeps Nimbus strictly read-only per G2], or (b) refresh tokens itself with the refreshToken [writes to Claude Code's Keychain item; refresh-token rotation could break the CLI login], or (c) use the pasted sessionKey cookie instead?

## Decided by Pier (2026-07-10)

1. **Data source: both** — session-key endpoint primary, local JSONL fallback.
2. **Keeper: haiku model.** Schedule anchor is **read from the actual observed reset time**, with a settings field letting the user override/input it manually.
3. **Discharged cloud shows both** the 5h window and the 7-day cap.

## Session log

- 2026-07-10 — STEP 0: scaffolded the control layer (4 files). No feature code written.
- 2026-07-10 — Pier decided all 3 open decisions (see "Decided by Pier"). G7 verification complete: usage endpoint, auth, and response schema recorded in FACTS.md with source links. P1 is unblocked.
- 2026-07-10 — P1 built: `nimbus/` package (models, config+Keychain, api fetcher, jsonl fallback, status CLI). Verified: JSONL fallback derives the live window from real logs (opened 13:08 → resets 18:08, utilization honestly unknown); simulated network cut with key → clean JSONL fallback; no key + no JSONL → `disconnected` (exit 2). **Not yet verified: live API % (needs Pier's sessionKey via `python -m nimbus.status --set-key`). P1 done-when therefore NOT passed — box stays unchecked.**

## Notes / blockers

- Endpoint is internal/undocumented (see FACTS.md caveat) — fetcher must degrade to JSONL + honest disconnected state (G6) on any failure.
