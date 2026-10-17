"""Live smoke test: Telegram owner-bot gateway round-trip.

STATUS: BLOCKED — awaiting real credentials via a secure channel.
Credentials are provided via environment variables only and are never committed.

What this test does (only when credentials are present):
1. ``getMe`` against the Telegram Bot API — proves the bot token is
   valid without sending anything.
2. A direct ``TelegramChannel.send`` to the owner chat — proves Bot API
   delivery to the owner.
3. A ``TelegramGateway`` round-trip: a synthetic inbound message from
   the owner chat is routed through the real gateway to an echo agent,
   and the echo reply is sent back out through the same real channel
   (the owner sees both messages in their Telegram client).

What it does NOT do:
- No long polling (``connect()`` is never called), so it cannot 409
  with a running bot instance.
- No human reply is required; the "round-trip" is gateway -> Bot API
  send, observed by the owner in Telegram.
- No fake/dummy credentials: placeholder or malformed tokens SKIP,
  they are never used to claim a live result.

Credentials:
- ``TELEGRAM_BOT_TOKEN`` — bot token, env var only. Never hardcoded,
  never logged, never in any file.
- ``TELEGRAM_OWNER_CHAT_ID`` — owner chat id (also the allowlist).

If either is absent, the test SKIPs with "credentials not provided"
(fail-closed, never a confusing failure).

Run (only with real credentials from a secure channel)::

    TELEGRAM_BOT_TOKEN=... TELEGRAM_OWNER_CHAT_ID=... \\
        pytest tests/smoke/test_telegram_owner_bot.py -m live_channel -v
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

from openjarvis.channels._stubs import ChannelMessage
from openjarvis.channels.telegram import TelegramChannel
from openjarvis.channels.telegram_gateway import TelegramGateway

_PLACEHOLDER_HINTS = (
    "test",
    "dummy",
    "fake",
    "placeholder",
    "replace",
    "your_",
    "xxx",
    "example",
    "changeme",
)


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(hint in lowered for hint in _PLACEHOLDER_HINTS)


def _assert_get_me(token: str) -> None:
    """Prove the token is valid via getMe. Never logs the token."""
    resp = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15.0)
    assert resp.status_code == 200, (
        f"Telegram getMe failed with HTTP {resp.status_code}"
    )
    assert resp.json().get("ok") is True, "Telegram getMe did not return ok"


@pytest.mark.live_channel
@pytest.mark.live
def test_owner_bot_gateway_round_trip() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    owner_chat_id = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "")
    if not token or not owner_chat_id:
        pytest.skip(
            "credentials not provided: set TELEGRAM_BOT_TOKEN and "
            "TELEGRAM_OWNER_CHAT_ID via a secure channel"
        )
    if _looks_like_placeholder(token) or _looks_like_placeholder(owner_chat_id):
        pytest.skip("placeholder credentials detected — not a live test, skipping")
    if ":" not in token:
        pytest.skip("TELEGRAM_BOT_TOKEN is malformed (no ':' separator)")

    _assert_get_me(token)

    # Send-only: connect() is never called, so no long-polling conflict.
    channel = TelegramChannel(bot_token=token, allowed_chat_ids=owner_chat_id)
    probe = f"Jarvis smoke probe {uuid.uuid4().hex[:8]}"
    assert channel.send(owner_chat_id, probe) is True, (
        "direct send to owner chat failed"
    )

    gateway = TelegramGateway(
        channel,
        lambda text: f"smoke echo {text}",
        allowed_chat_ids=owner_chat_id,
    )
    try:
        inbound = ChannelMessage(
            channel="telegram",
            sender=owner_chat_id,
            content=probe,
            message_id="",  # empty => no reply_to_message_id on the send
            conversation_id=owner_chat_id,
        )
        reply = gateway.handle_message(inbound)
    finally:
        gateway.shutdown()
    assert reply is not None, "gateway produced no reply"
    assert probe in reply, "gateway reply did not echo the probe"
