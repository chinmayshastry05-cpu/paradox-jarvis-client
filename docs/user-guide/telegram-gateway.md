# Telegram gateway (Phase 4)

Admin-only Telegram access via the Bot API (free). No MTProto / userbot
exists and none is planned — that is BLOCKED.

## Components

| Piece | Role |
|---|---|
| `channels/telegram.py` — `TelegramChannel` | Bot API long polling + `sendMessage`. Owns the bot token. |
| `channels/telegram_gateway.py` — `TelegramGateway` | Routes inbound messages to an existing agent/system and runs the approval round-trip. Builds **no** parallel agent. |
| `security/confirmation.py` — `ConfirmationGate` | The central single-use, exact-arguments approval gate. The gateway never bypasses it. |
| `security/delivery_redaction.py` | Fail-closed redaction of outbound replies, prompts, and bus events. |

## Setup

```toml
[channel]
enabled = true
default_channel = "telegram"

[channel.telegram]
# Token from the TELEGRAM_BOT_TOKEN environment variable (or this key).
# NEVER commit a real token, NEVER send one over mail/chat/Telegram.
bot_token = ""
# Admin-only: the chat id(s) allowed to talk to the bot AND to approve.
# An empty allowlist is NOT admin-only: normal chat still flows through
# the channel, but confirmations are refused entirely.
allowed_chat_ids = "111"
```

```python
from openjarvis.channels.telegram import TelegramChannel
from openjarvis.channels.telegram_gateway import TelegramGateway
from openjarvis.security.confirmation import ConfirmationGate

gate = ConfirmationGate()  # SAME instance the agent's ToolExecutor uses
gateway = TelegramGateway(
    TelegramChannel(bot_token=""),  # token from config/env inside the channel
    agent=my_system,               # JarvisSystem (ask) / agent (run) / callable
    confirmation_gate=gate,
    allowed_chat_ids="111",
)
gateway.attach()  # registers on_message; use INSTEAD of JarvisSystem.wire_channel
gateway.start()   # starts Bot API long polling
```

`serve.py` is not yet switched to the gateway — it still uses
`JarvisSystem.wire_channel`. Switching it is a coordinator decision: the
gateway must share the gate instance the agent's `ToolExecutor` uses,
or Telegram approvals would never be consumed.

## Message flow

```
Telegram update (Bot API long poll)
  -> TelegramChannel: allowlist check (unlisted chats dropped, no reply)
  -> TelegramGateway.handle_message
       ├─ "YES <id>" / "NO <id>" matching a pending request FROM THE SAME
       │   chat -> confirmation reply (see below); never reaches the agent
       ├─ anything else -> agent.run / agent.ask / callable
       │     └─ consequential tools -> ToolExecutor -> ConfirmationGate:
       │        no valid approval -> tool FAILS CLOSED, no execution
       └─ reply -> redact_text -> channel.send (redacts again at last hop)
```

Bus events (`CHANNEL_MESSAGE_RECEIVED` / `CHANNEL_MESSAGE_SENT`) carry
redacted content. Handlers and the agent still receive the raw inbound
message — the live user→agent queue is the agent's input (Phase 1
boundary) — but nothing raw is logged or stored in event history by the
gateway or the channel.

## Confirmation flow (the gate, via Telegram)

1. Trusted operator code (never a Telegram user) calls
   `gateway.request_confirmation(tool_name, arguments, chat_id)`. This
   registers a **pending request, not an approval**, and sends the admin
   a prompt with **redacted** arguments:
   `Reply "YES <id>" to approve this exact action once, or "NO <id>" to deny.`
   If the prompt cannot be delivered, no pending request is left behind.
2. Admin replies `YES <id>` from the same chat. The gateway calls
   `gate.grant(tool, exact-arguments)` — the approval now lives in the
   central gate until the `ToolExecutor` consumes it exactly once via
   `consume_matching` for that exact tool + arguments, or it expires.
3. `NO <id>` grants nothing. A `YES` for an unknown, expired, or
   other-chat id grants nothing. A second `YES` for the same id grants
   nothing (the pending entry is consumed on first use). A pending
   request alone never makes a tool executable.

The gate approval token is never sent over Telegram — it is only the
server-side revocation handle (revoke via `POST /v1/approvals/tool/revoke`).

## What is NOT done / NOT verified

- **No live Telegram testing**: no real bot token, no live send/receive,
  no live Telegram→approval round-trip. All tests use a fake channel,
  a fake agent, and the real gate, with `httpx` mocked.
- No webhook endpoint: long polling only. No public URL to expose.
- No MTProto / userbot. No paid services. No new dependencies.
- `serve.py` still wires channels via `wire_channel`, not the gateway.
