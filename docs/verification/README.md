# Verification — Paradox Jarvis (client edition)

Raw logs backing the checks listed in the top-level README. Paths are
sanitized for privacy (home directory shown as `~`). No claims beyond
these tests: desktop automation, Telegram delivery, and cloud engines
are not live-tested in this edition's verification set.

| Log | Check | Result |
| --- | --- | --- |
| `installer-test.log` | Clean-environment `install.sh` run to completion | PENDING |
| `wizard-client-run.log` | Setup wizard run writing a config with placeholder values | PENDING |
| `ollama-chat-roundtrip.log` | One real local Ollama chat round trip through the app | PENDING |
| CI (GitHub Actions) | Unit CI on the pushed HEAD | PENDING |

## Privacy note

Logs are sanitized before committing: home paths replaced with `~`,
and any credential, token, or secret redacted. The wizard never stores
API keys or bot tokens; only the Telegram admin chat ID is saved to
config.
