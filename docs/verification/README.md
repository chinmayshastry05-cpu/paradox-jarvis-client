# Verification logs

Logs backing the verification claims in the owner verification reports.
Paths sanitized for privacy (local machine paths replaced with `~`).
Each file is the direct output of the run it names. No secrets, tokens,
or credentials appear in any of these logs (checked before commit:
only test names and env-var *names* match secret patterns).

Note: the repo history was squashed to a single commit before
publication; commit SHAs cited below refer to the pre-publication
history and no longer resolve.

| Log | What it proves |
|---|---|
| `tts-smoke-rerun5.log` | Kokoro TTS smoke: 1 passed in 374.35s, exit 0 (commit `caccf1ca`) |
| `live-obsidian.log` | Obsidian connector live smoke: 1 passed in 120.23s |
| `live-gmail-channel.log` | Gmail live-channel smoke: 1 skipped, 18 deselected (no credentials; NOT a pass) |
| `live-external2.log` | External comparison: 3 skipped (Hermes/OpenClaw paths unconfigured) |
| `live-pearl.log` | CPU Pearl: 1 skipped, 9 deselected (pearl deps absent) |
| `live-integration4.log` | Skills integration live (Ollama qwen3.5:4b): 2 passed / 3 failed (3 failures = no skills installed) |
| `hermes-proof.log` | Hermes binary via local Ollama: `hermes --cli -z "What is 2+2?"` → `4`, exit 0 |
| `task-e-full-suite-final.log` | Local full suite (HEAD `cb86d633`, `-n auto`, `not live and not cloud and not hub`): 11 failed / 9938 passed / 103 skipped / 4 xfailed / 1 xpassed, exit 1. CI on the same commit was green; the 11 local failures are local-environment causes (see the owner verification reports) |
| `task-e-full-suite-attempt1-killed-by-restart.log` | Earlier sequential full-suite attempt, killed by a VM runtime restart at ~42% |
| `task-e-full-suite-attempt2-killed-by-restart.log` | Earlier sequential full-suite attempt, killed by a VM runtime restart at ~50% |
| `live-telegram-owner-bot.log` | Telegram owner-bot smoke, first run: `httpx.RemoteProtocolError` during getMe (VM proxy cannot reach `api.telegram.org`) |
| `live-telegram-owner-bot-rerun.log` | Telegram owner-bot smoke, rerun: same transport failure |
| `wizard-live-run.log` | Live `jarvis setup` run, skip path: config written, Kokoro on, desktop permissions check |
| `wizard-live-run2.log` | Live `jarvis setup` run, full path: Telegram chat ID saved (token never written to config), Kokoro off, config-exists skip on re-run |
| `installer-test.log` | Clean-environment `install.sh` test: clone → uv sync → Ollama + starter model → wizard (scripted answers). Paths sanitized for privacy |
| `ci-fix-speech-routes.log` | CI-fix verification: `tests/server/test_speech_routes.py`, 21 passed (the two concurrent-health tests fixed for the `get_tts_backend(enabled=...)` signature) |
