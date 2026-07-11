# Nimbus ☁️

<p align="center">
  <img src="assets/hero.png" width="180" alt="Nimbus cloud at 72% charge">
</p>

A tiny macOS menu bar app that shows your Claude usage as a cloud. It starts
orange and drains to grey as the 5-hour window fills up, recharges as the
reset approaches, notifies you the moment usage is available again, and
(opt-in) sends one minimal message at each reset so your 5-hour windows stay
pinned to a predictable schedule.

There's also a **desktop pet**: a floating cloud widget you can drag anywhere
and resize from its corner grip, showing the live % and reset countdown.

## Cloud states

| <img src="assets/state_full.png" width="90"> | <img src="assets/state_partly.png" width="90"> | <img src="assets/state_thin.png" width="90"> | <img src="assets/state_discharged.png" width="90"> | <img src="assets/state_recharging.png" width="90"> | <img src="assets/state_disconnected.png" width="90"> |
|:---:|:---:|:---:|:---:|:---:|:---:|
| full<br>≥80% left | partly drained<br>79–40% | thin<br>39–15% | discharged<br><15% | recharging<br>(reset pending) | disconnected |

The images above are rendered by the app's own drawing code — what you see in
the menu bar and the desktop widget.

## Install

```sh
git clone https://github.com/0xPier/nimbus.git && cd nimbus
./install.sh      # venv + LaunchAgent, starts immediately, survives reboot
```

A short first-run wizard walks you through data sources, the desktop pet, and
the optional window keeper. `./uninstall.sh` removes everything and offers to
delete the Keychain item.

## Data sources (in order)

1. **Nimbus's own login** (recommended) — menu → *Connect live data (browser
   login)*, or `python -m nimbus.login`. One-time browser approval with a
   read-only scope; Nimbus keeps and refreshes its own token in its own
   Keychain item. Survives indefinitely.
2. **Claude Code OAuth token** (read-only) — reuses your existing `claude` CLI
   login. Zero setup, but the CLI's token expires roughly daily unless you
   use it often.
3. **claude.ai session key** — optional: `python -m nimbus.status --set-key`
   (stored only in the macOS Keychain).
4. **Local Claude Code logs** (`~/.claude/projects/`) — zero-network fallback;
   knows the window timing but shows utilization as honestly *unknown*.
5. Nothing available → the cloud shows a red slash. Nimbus never guesses.

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
  endpoints (`claude.ai`, `api.anthropic.com`) to read your usage numbers.
  No analytics, no telemetry, no third-party calls, no crash reporters.
- **Nothing sensitive is stored.** Credentials live exclusively in the macOS
  Keychain. The only files Nimbus writes are its settings, cached usage
  percentages/reset timestamps, and a keeper log containing timestamps only.
  Conversation content is never read, logged, or transmitted.
- **Read-only monitoring.** The monitoring path only ever *reads* usage data —
  it never sends messages, mutates settings, or touches conversations. The
  sole exception is the keeper ping described above, which you must opt into.

## Stack

Python 3.11+, [rumps](https://github.com/jaredks/rumps), keyring, requests,
AppKit (via pyobjc) for the drawn cloud and the desktop widget. Packaged as a
launchd LaunchAgent. No Electron, no databases.

## Disclaimer

Usage endpoints are Anthropic-internal and undocumented; they may change
without notice. If they break, Nimbus degrades to local log estimation and
says so — it never shows a number it can't back up.
