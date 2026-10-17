"""Tests for TelegramGateway — Telegram Bot API gateway (Phase 4).

No real Telegram connection: the channel is a fake (records sends,
delivers inbound messages synchronously), the agent is a fake, and the
ConfirmationGate is real. The only real Telegram code exercised is
TelegramChannel.send / bus-event redaction, with httpx mocked.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from openjarvis.channels._stubs import ChannelMessage
from openjarvis.channels.telegram import TelegramChannel
from openjarvis.channels.telegram_gateway import TelegramGateway
from openjarvis.core.events import EventBus, EventType
from openjarvis.security.confirmation import ConfirmationGate

SECRET = "sk-abcdefghij1234567890ABCDEFGH"
ADMIN_CHAT = "111"
OTHER_CHAT = "999"


class FakeChannel:
    """Minimal BaseChannel stand-in: records sends, no network."""

    def __init__(self, allowed_chat_ids: str = "") -> None:
        self._allowed_chat_ids = allowed_chat_ids
        self.sent: list[dict] = []
        self._handlers: list = []
        self.connected = False

    def on_message(self, handler):
        self._handlers.append(handler)

    def send(self, channel, content, *, conversation_id="", metadata=None):
        self.sent.append(
            {"channel": channel, "content": content, "conversation_id": conversation_id}
        )
        return True

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def deliver(self, msg: ChannelMessage):
        for handler in self._handlers:
            handler(msg)


class FakeAgent:
    """Agent stand-in: echoes, or returns a canned reply."""

    def __init__(self, reply: str = "hello back") -> None:
        self.reply = reply
        self.seen: list[str] = []

    def run(self, text: str):
        self.seen.append(text)
        return SimpleNamespace(content=self.reply)


def _msg(
    content: str, chat_id: str = ADMIN_CHAT, message_id: str = "7"
) -> ChannelMessage:
    return ChannelMessage(
        channel="telegram",
        sender="user-1",
        content=content,
        message_id=message_id,
        conversation_id=chat_id,
    )


def _gateway(**kwargs):
    channel = kwargs.pop("channel", FakeChannel(allowed_chat_ids=ADMIN_CHAT))
    agent = kwargs.pop("agent", FakeAgent())
    gate = kwargs.pop("gate", ConfirmationGate())
    gw = TelegramGateway(channel, agent, confirmation_gate=gate, **kwargs)
    gw.attach()
    return gw, channel, agent, gate


class TestRouting:
    def test_incoming_message_routes_to_agent_and_replies(self):
        gw, channel, agent, _ = _gateway()
        try:
            reply = gw.handle_message(_msg("ping"))
        finally:
            gw.shutdown()
        assert reply == "hello back"
        assert agent.seen == ["ping"]
        assert len(channel.sent) == 1
        assert channel.sent[0]["channel"] == ADMIN_CHAT
        assert channel.sent[0]["content"] == "hello back"
        # Reply reference is the inbound message id, not the chat id.
        assert channel.sent[0]["conversation_id"] == "7"

    def test_callable_agent_shape(self):
        gw, channel, _, _ = _gateway(agent=lambda text: f"echo:{text}")
        try:
            assert gw.handle_message(_msg("hi")) == "echo:hi"
        finally:
            gw.shutdown()

    def test_ask_dict_agent_shape(self):
        system = SimpleNamespace(ask=lambda text: {"content": "via ask"})
        gw, channel, _, _ = _gateway(agent=system)
        try:
            assert gw.handle_message(_msg("hi")) == "via ask"
        finally:
            gw.shutdown()

    def test_unusable_agent_rejected_at_construction(self):
        with pytest.raises(TypeError):
            TelegramGateway(FakeChannel(), object())

    def test_non_telegram_message_ignored(self):
        gw, channel, agent, _ = _gateway()
        try:
            msg = _msg("ping")
            msg.channel = "discord"
            assert gw.handle_message(msg) is None
        finally:
            gw.shutdown()
        assert agent.seen == []
        assert channel.sent == []

    def test_unlisted_chat_dropped_never_reaches_agent(self):
        gw, channel, agent, _ = _gateway()
        try:
            assert gw.handle_message(_msg("ping", chat_id=OTHER_CHAT)) is None
        finally:
            gw.shutdown()
        assert agent.seen == []
        assert channel.sent == []

    def test_agent_exception_yields_generic_reply_no_leak(self):
        def _boom(text):
            raise RuntimeError(f"db exploded, password = '{SECRET}'")

        gw, channel, _, _ = _gateway(agent=_boom)
        try:
            reply = gw.handle_message(_msg("ping"))
        finally:
            gw.shutdown()
        assert reply is not None
        assert SECRET not in reply
        assert "db exploded" not in reply
        assert "password" not in reply.lower()
        assert channel.sent and SECRET not in channel.sent[0]["content"]

    def test_empty_agent_reply_sends_nothing(self):
        gw, channel, _, _ = _gateway(agent=FakeAgent(reply=""))
        try:
            assert gw.handle_message(_msg("ping")) is None
        finally:
            gw.shutdown()
        assert channel.sent == []

    def test_start_stop_delegate_to_channel(self):
        gw, channel, _, _ = _gateway()
        try:
            gw.start()
            assert channel.connected is True
            gw.stop()
            assert channel.connected is False
        finally:
            gw.shutdown()


class TestRedaction:
    def test_outbound_reply_secret_redacted_before_send(self):
        gw, channel, _, _ = _gateway(agent=FakeAgent(reply=f"key is {SECRET}"))
        try:
            reply = gw.handle_message(_msg("ping"))
        finally:
            gw.shutdown()
        assert SECRET not in reply
        assert SECRET not in channel.sent[0]["content"]
        assert "REDACTED" in channel.sent[0]["content"]

    def test_confirmation_prompt_args_redacted(self):
        gw, channel, _, _ = _gateway()
        try:
            gw.request_confirmation(
                "send_email", {"to": "a@b.c", "api_key": f'"{SECRET}"'}, ADMIN_CHAT
            )
        finally:
            gw.shutdown()
        prompt = channel.sent[0]["content"]
        assert SECRET not in prompt
        assert "REDACTED" in prompt

    def test_channel_send_redacts_at_last_hop(self):
        """Even a direct TelegramChannel.send caller cannot leak a secret:
        send() redacts before the Bot API call."""
        bus = EventBus(record_history=True)
        ch = TelegramChannel(bot_token="123:ABC", bus=bus)
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("httpx.post", return_value=mock_response) as mock_post:
            assert ch.send(ADMIN_CHAT, f"leak {SECRET}") is True
        payload = mock_post.call_args[1]["json"]
        assert SECRET not in payload["text"]
        assert "REDACTED" in payload["text"]
        sent_events = [
            e for e in bus.history if e.event_type == EventType.CHANNEL_MESSAGE_SENT
        ]
        assert sent_events and SECRET not in str(sent_events[0].data)


class TestConfirmationGateFlow:
    def test_yes_grants_exact_approval_consumable_once(self):
        gw, channel, _, gate = _gateway()
        try:
            req_id = gw.request_confirmation(
                "file_write", {"path": "/tmp/x", "content": "hi"}, ADMIN_CHAT
            )
            assert req_id
            assert len(channel.sent) == 1  # the prompt
            reply = gw.handle_message(_msg(f"YES {req_id}"))
            assert "Approved" in reply
            # The grant is consumable for exactly these arguments...
            assert (
                gate.consume_matching("file_write", {"path": "/tmp/x", "content": "hi"})
                is True
            )
            # ...and single-use: a replay consumes nothing.
            assert (
                gate.consume_matching("file_write", {"path": "/tmp/x", "content": "hi"})
                is False
            )
        finally:
            gw.shutdown()

    def test_yes_does_not_grant_tampered_arguments(self):
        gw, channel, _, gate = _gateway()
        try:
            req_id = gw.request_confirmation(
                "file_write", {"path": "/tmp/x", "content": "hi"}, ADMIN_CHAT
            )
            gw.handle_message(_msg(f"YES {req_id}"))
            # Tampered arguments must not match the granted approval.
            assert (
                gate.consume_matching(
                    "file_write", {"path": "/tmp/evil", "content": "hi"}
                )
                is False
            )
            assert gate.consume_matching("other_tool", {"path": "/tmp/x"}) is False
        finally:
            gw.shutdown()

    def test_second_yes_grants_nothing(self):
        gw, channel, _, gate = _gateway()
        try:
            req_id = gw.request_confirmation("shell", {"cmd": "ls"}, ADMIN_CHAT)
            gw.handle_message(_msg(f"YES {req_id}"))
            assert gate.consume_matching("shell", {"cmd": "ls"}) is True
            # Replay: pending is gone, so this falls through to the agent
            # (fake agent replies) and grants nothing new.
            gw.handle_message(_msg(f"YES {req_id}"))
            assert gate.consume_matching("shell", {"cmd": "ls"}) is False
        finally:
            gw.shutdown()

    def test_no_denies_and_grants_nothing(self):
        gw, channel, _, gate = _gateway()
        try:
            req_id = gw.request_confirmation("shell", {"cmd": "ls"}, ADMIN_CHAT)
            reply = gw.handle_message(_msg(f"NO {req_id}"))
            assert "Denied" in reply
            assert gate.consume_matching("shell", {"cmd": "ls"}) is False
        finally:
            gw.shutdown()

    def test_yes_from_other_chat_grants_nothing(self):
        gw, channel, _, gate = _gateway()
        try:
            req_id = gw.request_confirmation("shell", {"cmd": "ls"}, ADMIN_CHAT)
            # Other chat's YES must not approve: it falls through to the
            # agent (which is allowlist-dropped), and the pending stays.
            gw.handle_message(_msg(f"YES {req_id}", chat_id=OTHER_CHAT))
            assert gate.consume_matching("shell", {"cmd": "ls"}) is False
            assert len(gw.list_pending()) == 1
            # The admin's YES still works afterwards.
            gw.handle_message(_msg(f"YES {req_id}"))
            assert gate.consume_matching("shell", {"cmd": "ls"}) is True
        finally:
            gw.shutdown()

    def test_yes_for_unknown_id_grants_nothing(self):
        gw, channel, agent, gate = _gateway()
        try:
            reply = gw.handle_message(_msg("YES deadbeefdeadbeef"))
            # Falls through to the agent as ordinary chat.
            assert reply == "hello back"
            assert agent.seen == ["YES deadbeefdeadbeef"]
            assert gate.consume_matching("shell", {"cmd": "ls"}) is False
        finally:
            gw.shutdown()

    def test_expired_pending_yes_grants_nothing(self):
        gw, channel, _, gate = _gateway(confirmation_ttl_seconds=0.05)
        try:
            req_id = gw.request_confirmation("shell", {"cmd": "ls"}, ADMIN_CHAT)
            time.sleep(0.1)
            gw.handle_message(_msg(f"YES {req_id}"))
            assert gate.consume_matching("shell", {"cmd": "ls"}) is False
        finally:
            gw.shutdown()

    def test_pending_is_not_an_approval(self):
        """Registering a pending request alone must not make the tool
        executable: consume_matching finds nothing until YES."""
        gw, channel, _, gate = _gateway()
        try:
            gw.request_confirmation("shell", {"cmd": "ls"}, ADMIN_CHAT)
            assert gate.consume_matching("shell", {"cmd": "ls"}) is False
        finally:
            gw.shutdown()

    def test_gate_token_never_sent_over_telegram(self):
        gw, channel, _, gate = _gateway()
        try:
            req_id = gw.request_confirmation("shell", {"cmd": "ls"}, ADMIN_CHAT)
            gw.handle_message(_msg(f"YES {req_id}"))
            tokens = list(gate._approvals.keys())
            assert tokens  # a grant really exists server-side
            for sent in channel.sent:
                for token in tokens:
                    assert token not in sent["content"]
            assert req_id not in tokens  # request id != gate token
        finally:
            gw.shutdown()

    def test_empty_allowlist_refuses_confirmations(self):
        channel = FakeChannel(allowed_chat_ids="")
        gate = ConfirmationGate()
        gw = TelegramGateway(channel, FakeAgent(), confirmation_gate=gate)
        try:
            with pytest.raises(ValueError, match="non-empty allowed_chat_ids"):
                gw.request_confirmation("shell", {"cmd": "ls"}, ADMIN_CHAT)
            # And a YES-shaped message can never grant without a pending.
            gw.handle_message(_msg("YES abc123"))
            assert gate.consume_matching("shell", {"cmd": "ls"}) is False
        finally:
            gw.shutdown()

    def test_request_for_non_allowlisted_chat_refused(self):
        gw, channel, _, gate = _gateway()
        try:
            with pytest.raises(ValueError, match="not in the admin allowlist"):
                gw.request_confirmation("shell", {"cmd": "ls"}, OTHER_CHAT)
            assert gw.list_pending() == []
        finally:
            gw.shutdown()

    def test_undelivered_prompt_leaves_no_pending(self):
        channel = FakeChannel(allowed_chat_ids=ADMIN_CHAT)
        channel.send = lambda *a, **k: False
        gw = TelegramGateway(channel, FakeAgent(), confirmation_gate=ConfirmationGate())
        try:
            with pytest.raises(RuntimeError, match="could not be delivered"):
                gw.request_confirmation("shell", {"cmd": "ls"}, ADMIN_CHAT)
            assert gw.list_pending() == []
        finally:
            gw.shutdown()

    def test_list_pending_hides_arguments(self):
        gw, channel, _, _ = _gateway()
        try:
            gw.request_confirmation(
                "shell", {"cmd": "rm -rf /", "secret": SECRET}, ADMIN_CHAT
            )
            pending = gw.list_pending()
            assert len(pending) == 1
            assert "secret" not in str(pending)
            assert SECRET not in str(pending)
        finally:
            gw.shutdown()

    def test_shared_gate_with_executor_consumes_approval(self):
        """End-to-end gate semantics: the same gate instance the gateway
        grants into is the one the ToolExecutor consumes from."""
        from openjarvis.tools._stubs import (
            BaseTool,
            ToolCall,
            ToolExecutor,
            ToolResult,
            ToolSpec,
        )

        class ConfirmTool(BaseTool):
            tool_id = "confirm_tool"

            @property
            def spec(self):
                return ToolSpec(
                    name="confirm_tool",
                    description="A confirmation-gated tool.",
                    requires_confirmation=True,
                    timeout_seconds=5,
                )

            def execute(self, **kwargs):
                return ToolResult(tool_name="confirm_tool", content="ran", success=True)

        gate = ConfirmationGate()
        executor = ToolExecutor([ConfirmTool()], confirmation_gate=gate)
        gw, channel, _, _ = _gateway(gate=gate)
        try:
            # No approval yet: the executor fails closed.
            denied = executor.execute(
                ToolCall(id="1", name="confirm_tool", arguments='{"x": 1}')
            )
            assert denied.success is False
            # Admin approves exactly these arguments via Telegram.
            req_id = gw.request_confirmation("confirm_tool", {"x": 1}, ADMIN_CHAT)
            gw.handle_message(_msg(f"YES {req_id}"))
            # Now the executor consumes the Telegram-granted approval.
            ok = executor.execute(
                ToolCall(id="2", name="confirm_tool", arguments='{"x": 1}')
            )
            assert ok.success is True
        finally:
            gw.shutdown()
