# FACTS.md — canonical facts for Nimbus

**Precedence rule: if a fact here contradicts any other doc or your memory, this file wins. Cite this file, not your memory.**

Extend this file with **verified values only** — every added fact needs a source link. Unverified → mark `[VERIFY]` and escalate to Pier per G7.

## Usage windows

- The 5-hour window is rolling: it **starts at the first message sent** and resets 5h later; a subscription also has a 7-day cap. Limits are shared across claude.ai, Claude Code, desktop and mobile.
- Therefore "pinning": one throwaway first message at reset time makes every window start on a predictable clock (e.g. 07:00 / 12:00 / 17:00 / 22:00).

## Keeper

- Keeper command shape: `claude -p "Reply with exactly: ok" --model sonnet` (haiku variant allowed). Requires `claude` CLI on PATH and an active login. Timeout 60s; on failure, one retry after 5 min, then notify and give up (G3).

## Data sources

- Local data source: Claude Code writes session JSONL under `~/.claude/projects/` — usable for usage estimation without any network call.
- Remote data source: session-key-authenticated usage endpoint — **[VERIFY per G7 before use; record endpoint, header, response schema, and source link here]**.

## UI

- Cloud states (menu bar template icons): ☁️ full ≥80% remaining → partly-drained 79–40% → thin 39–15% → ⚡ discharged <15% or locked out → 🔌 recharging (locked, reset pending) → ⛔ disconnected (G6).
- Poll interval default 120s; back off to 300s when idle.
