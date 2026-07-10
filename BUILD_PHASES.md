# BUILD_PHASES.md — phases and done-when checks

Phase advancement is gated by the vetting gate (step 6 in `CLAUDE.md`): advance only when the current phase's done-when check has actually passed, and record it in `PROGRESS.md`.

- **P1 — Data layer.** Fetch/parse current 5h + weekly utilization and reset timestamps (endpoint per G7, JSONL fallback). *Done-when:* `python -m nimbus.status` prints live % and reset time for both windows, and prints `disconnected` cleanly when the network is cut.
- **P2 — Cloud in the menu bar.** rumps app, 6 icon states, tooltip with % and countdown, dropdown with details + settings. *Done-when:* icon visibly transitions across all states when fed the debug fixture (fixtures allowed only behind a `--debug` flag, G6).
- **P3 — Notifications.** macOS notification the moment a window resets ("☁️ Cloud recharged — usage available"), plus optional 80%/90% warnings. *Done-when:* a simulated reset fires exactly one notification.
- **P4 — Window keeper (opt-in).** Settings toggle with the usage-cost disclosure; at each reset, one CLI ping per G3, then re-poll to confirm the new window started; log only timestamps. *Done-when:* with the toggle on, a reset triggers exactly one `claude -p` call and `PROGRESS.md` shows the confirmed new reset time; with the toggle off, zero calls.
- **P5 — Ship.** launchd LaunchAgent, install/uninstall script, README with a privacy section restating G1/G2. *Done-when:* fresh install via script → app survives reboot → uninstall leaves nothing behind except the Keychain item, which it offers to delete.
