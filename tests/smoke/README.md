# Live smoke-test harnesses (prepared, NOT run live)

STATUS: **BLOCKED — awaiting credentials via a secure channel.**
Credentials are provided via environment variables only and are never committed.
No live test has been run. Nothing here claims a live result.

## Files

- `test_telegram_admin_bot.py` — Telegram admin-bot gateway round-trip.
- `test_free_tts.py` — real free TTS synthesis (local Kokoro by default).

## Telegram admin-bot smoke test

```sh
TELEGRAM_BOT_TOKEN=... TELEGRAM_ADMIN_CHAT_ID=... \
    pytest tests/smoke/test_telegram_admin_bot.py -m live_channel -v
```

Steps: `getMe` (proves the token) → direct `TelegramChannel.send` to the
admin chat (proves Bot API delivery) → `TelegramGateway` round-trip with
an echo agent (proves gateway routing + reply send). Send-only: `connect()`
is never called, so it cannot 409 with a running bot instance.

Credentials come ONLY from `TELEGRAM_BOT_TOKEN` /
`TELEGRAM_ADMIN_CHAT_ID` env vars. Missing → SKIP ("credentials not
provided"). Placeholder / malformed tokens → SKIP, never used to claim
a live result. The token is never hardcoded, logged, or written to any
file.

## Free TTS smoke test

```sh
pytest tests/smoke/test_free_tts.py -m live -v
```

Synthesizes a short phrase with `TTS_SMOKE_BACKEND` (default `kokoro`:
local, open-source, keyless, zero spend) and asserts non-empty audio,
positive duration, a valid WAV header, and a round-tripped saved file.
Optional: `TTS_SMOKE_TEXT`, `TTS_SMOKE_VOICE`. Backend unavailable /
not installed → SKIP. No API key is read, passed, or logged by this
harness; a cloud backend would use its own env configuration only.

## Rules

- Free only, zero spend. No credentials anywhere (chat/mail/files/logs/code).
- No Kaggle/GPU. No live testing until unblocked. No ready/fully-secured claim.
- These tests are excluded from the default lane: Telegram carries
  `live` + `live_channel`, TTS carries `live` + `slow`
  (`make test` selects `-m "not live and not cloud and not hub"`).
  Without credentials they SKIP rather than fail.
