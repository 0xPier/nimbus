# Nimbus ☁️

A tiny macOS menu bar app that shows your Claude usage as a cloud: it drains
as the 5-hour window fills up, recharges as the reset approaches, notifies you
the moment usage is available again, and (opt-in) sends one minimal message at
each reset so your 5-hour windows stay pinned to a predictable schedule.

## Cloud states

☁️ full (≥80% remaining) · 🌥 partly drained (79–40%) · 🌫 thin (39–15%) ·
⚡ discharged (<15%) · 🔌 recharging (locked, reset pending) · ⛔ disconnected

## Install

```sh
./install.sh      # venv + LaunchAgent, starts immediately, survives reboot
./uninstall.sh    # removes everything; offers to delete the Keychain item
```

## Data sources (in order)

1. **Claude Code OAuth token** (read-only) — reuses your existing `claude` CLI
   login from the Keychain. No setup needed.
2. **claude.ai session key** — optional: `python -m nimbus.status --set-key`
   (stored only in the macOS Keychain).
3. **Local Claude Code logs** (`~/.claude/projects/`) — zero-network fallback;
   knows the window timing but shows utilization as honestly *unknown*.
4. Nothing available → the cloud shows ⛔ disconnected. Nimbus never guesses.

Check from a terminal any time: `.venv/bin/python -m nimbus.status`

## Window keeper (opt-in, off by default)

Enabling "Window keeper" in the menu sends **exactly one** minimal CLI message
(`claude -p "Reply with exactly: ok" --model haiku`) at each reset, so every
5-hour window starts on a fixed clock instead of whenever you happen to send
your first message. **This consumes a small amount of your usage each cycle** —
that's why it's off until you explicitly enable it. On failure it retries once
after 5 minutes, then gives up until the next reset. It will never send more.

## Privacy

- **Nothing leaves your machine.** Nimbus talks only to Anthropic's own
  endpoints to read your usage numbers. No analytics, no telemetry, no
  third-party calls, no crash reporters.
- **Nothing sensitive is stored.** Credentials live exclusively in the macOS
  Keychain. The only files Nimbus writes are its settings, cached usage
  percentages/reset timestamps, and a keeper log containing timestamps only.
  Conversation content is never read, logged, or transmitted.
- **Read-only monitoring.** The monitoring path only ever *reads* usage data —
  it never sends messages, mutates settings, or touches conversations. The
  sole exception is the keeper ping described above, which you must opt into.

## Stack

Python 3.11+, [rumps](https://github.com/jaredks/rumps), keyring, requests.
Packaged as a launchd LaunchAgent. No Electron, no databases.
