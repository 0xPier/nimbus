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
- Remote data source — **verified per G7 on 2026-07-10** from Usage4Claude source (`Usage4Claude/Services/ClaudeAPIService.swift` and `Models/ClaudeAPIResponseModels.swift`, https://github.com/f-is-h/Usage4Claude):
  - Usage: `GET https://claude.ai/api/organizations/{org_id}/usage`
  - Org lookup: `GET https://claude.ai/api/organizations` (org id also appears in the `lastActiveOrg` cookie)
  - Auth: `Cookie: sessionKey=sk-ant-sid...` (session key from claude.ai cookies, stored in Keychain per G1). Usage4Claude notes Cloudflare may additionally require `cf_clearance`/`__cf_bm` cookies — treat a 403 as "disconnected" (G6), never scrape them via UI automation (G4).
  - Response schema: `{ "five_hour": {"utilization": <0–100 float>, "resets_at": "<ISO 8601>"}, "seven_day": {...same}, "seven_day_opus": {...}, "seven_day_sonnet": {...} }` — `seven_day*` fields optional.
  - Caveat: internal, undocumented endpoint; may change without notice. If it breaks, fall back to JSONL and show honest state per G6.
- OAuth data source — **verified per G7 on 2026-07-10** from Usage4Claude source (`Usage4Claude/Services/ClaudeOAuth/ClaudeOAuthConfig.swift`, https://github.com/f-is-h/Usage4Claude), **Pier-approved for monitoring**:
  - Usage: `GET https://api.anthropic.com/api/oauth/usage`
  - Headers: `Authorization: Bearer <accessToken>` + `anthropic-beta: oauth-2025-04-20`
  - Same response schema as the sessionKey endpoint (`five_hour`/`seven_day`/`seven_day_opus`/`seven_day_sonnet`, each `utilization` + `resets_at`).
  - Token source: Claude Code's existing login, macOS Keychain item service `Claude Code-credentials` (JSON: `claudeAiOauth.accessToken`, `refreshToken`, `expiresAt` ms-epoch). Nimbus reads it **read-only** (G2) and never refreshes or mutates it — an expired token means "fall back", Claude Code refreshes it itself on next use.
  - Source order in Nimbus: OAuth → sessionKey endpoint → local JSONL → disconnected.

## UI

- Cloud states (menu bar template icons): ☁️ full ≥80% remaining → partly-drained 79–40% → thin 39–15% → ⚡ discharged <15% or locked out → 🔌 recharging (locked, reset pending) → ⛔ disconnected (G6).
- Poll interval default 300s (configurable via settings `poll_interval`); 600s when idle (discharged/recharging), 900s after an HTTP 429. Rationale: 300s is ~1.7% of the 5h window — plenty of resolution — and the oauth usage endpoint rate-limits aggressive pollers (observed 2026-07-10).
