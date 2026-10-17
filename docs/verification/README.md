# Verification — Paradox Jarvis (client edition)

Raw logs backing the checks listed in the top-level README. Paths are
sanitized for privacy (home directory shown as `~`). No claims beyond
these tests: desktop automation, Telegram delivery, and cloud engines
are not live-tested in this edition's verification set.

| Log | Check | Result |
| --- | --- | --- |
| `installer-test.log` | Clean-environment `install.sh` run to completion | PASS — exit 0. Cloned the client repo, installed uv, synced the venv, installed Ollama (systemd service), ran the wizard, config written (engine llamacpp default — no engines detected; `tts_enabled = true`). Known pre-existing VM issue: `ollama pull qwen3:0.6b` failed TLS (proxy), installer warned and continued. |
| `wizard-client-run.log` | Setup wizard run writing a config with placeholder values | PASS — exit 0. Engine ollama (answered), Telegram admin bot with a placeholder token (getMe unreachable, tolerated), admin chat ID `123456789` saved, Kokoro on. Config verified: `allowed_chat_ids = "123456789"`, `tts_enabled = true`, token 0 occurrences in config and log. |
| `ollama-chat-roundtrip.log` | One real local Ollama chat round trip through the app | PASS — `jarvis ask` returned `4` for "What is 2+2?", exit 0, model `qwen3.5:4b` on local Ollama (user server, default port). Note: 3 earlier attempts failed because bracketed IPv6 values in this VM's `NO_PROXY` break httpx client construction (`InvalidURL`) — an environment quirk, not app code; a clean `NO_PROXY` fixed it. The `openjarvis_rust` rate-limiter warning is benign (Rust extension not built in the test venv). |
| CI (GitHub Actions) | Unit CI on the pushed HEAD | NOT RUN — no CI workflow exists on this repo yet (workflows not landed — owner web-session step). Local equivalent of the CI command (same pytest invocation, clean `NO_PROXY`): 19 failed / 9942 passed / 103 skipped / 4 xfailed / 1 xpassed, exit 1. Of the 19: 10 read the absent workflow files (they resolve when the workflows land); the other 9 match the known local-env failure categories on the ultra tree (torch, Pearl deps, DNS/proxy, subprocess timeout, numpy import). A first local run (296 failed) was invalid — this VM's bracketed-IPv6 `NO_PROXY` breaks httpx client construction; a targeted re-run of the 470 httpx-based tests passed 470/470 with a clean `NO_PROXY`. |

## Privacy note

Logs are sanitized before committing: home paths replaced with `~`,
and any credential, token, or secret redacted. The wizard never stores
API keys or bot tokens; only the Telegram admin chat ID is saved to
config.
