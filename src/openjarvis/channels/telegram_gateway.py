"""TelegramGateway — admin-only Telegram Bot API gateway.

Wires an existing :class:`~openjarvis.channels.telegram.TelegramChannel`
(Bot API long-polling, free) to an existing agent/system — it does NOT
build a parallel agent. Inbound Telegram messages flow:

1. ``TelegramChannel`` receives an update via Bot API long polling and
   enforces its ``allowed_chat_ids`` allowlist (unlisted chats are dropped
   before any handler runs).
2. The gateway's :meth:`TelegramGateway.handle_message` receives the
   :class:`~openjarvis.channels._stubs.ChannelMessage`. A message of the
   exact form ``YES <request-id>`` / ``NO <request-id>`` that matches a
   pending confirmation *from the same chat* is a confirmation reply
   (step 4). Anything else goes to the agent (step 3).
3. The agent runs (``run`` / ``ask`` / plain callable). Consequential
   tools inside that run go through the central
   :class:`~openjarvis.security.confirmation.ConfirmationGate` via the
   ``ToolExecutor`` — the gateway never bypasses it, never auto-approves,
   and never mints an approval on its own. Without a prior approval a
   confirmation-required tool fails closed with "requires confirmation".
4. Approvals are granted ONLY through :meth:`request_confirmation`,
   which trusted operator code calls when an action needs approval: it
   registers a *pending* request (not an approval), sends the admin a
   prompt with redacted arguments, and waits. The admin's ``YES <id>``
   then calls ``gate.grant(tool, exact-args)``; the grant lives in the
   gate until the ``ToolExecutor`` consumes it exactly once via
   ``consume_matching`` for that exact tool + arguments, or it expires.
   ``NO <id>`` grants nothing. A pending request is never itself an
   approval, a ``YES`` for an unknown / expired / other-chat request
   grants nothing, and a second ``YES`` for the same id grants nothing
   (the pending entry is removed on first use).

Admin-only rule: confirmations require a non-empty allowlist. If the
effective ``allowed_chat_ids`` is empty, :meth:`request_confirmation`
raises and no ``YES`` reply can ever grant — an empty allowlist is
treated as *not admin-only*. The gateway must share its
``ConfirmationGate`` instance with the ``ToolExecutor`` running the
agent, or approvals granted via Telegram would never be consumed.

Bot token: the gateway never sees, logs, or sends the token. The token
reaches ``TelegramChannel`` from config / the ``TELEGRAM_BOT_TOKEN``
environment variable only, is never hardcoded, and is never included
in any Telegram message, prompt, or log line. The gate approval token
is likewise never sent over Telegram (it is only the server-side
revocation handle).

Redaction: outbound replies and confirmation prompts are passed through
``delivery_redaction`` (fail-closed) before ``channel.send``. Inbound
content is NOT redacted before the agent sees it — same boundary as
Phase 1 (the live user→agent queue is the agent's input). No raw
message content, tool arguments, or tokens are ever logged.

Transport: Bot API long polling only (the existing ``TelegramChannel``).
No webhook endpoint is opened and no MTProto / userbot client exists
(MTProto is BLOCKED). No file I/O happens in this module, so there is
no TOCTOU surface here. No live Telegram connection is made in tests:
tests use a fake channel and a fake agent plus the real gate.
"""

from __future__ import annotations

import json
import logging
import re
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from openjarvis.channels._stubs import ChannelMessage
from openjarvis.security.confirmation import ConfirmationGate, canonical_arguments
from openjarvis.security.delivery_redaction import (
    redact_text,
    redact_value,
    safe_error_message,
)

logger = logging.getLogger(__name__)

_CONFIRM_RE = re.compile(r"^(YES|NO)\s+(\S+)\s*$", re.IGNORECASE)
_DEFAULT_CONFIRMATION_TTL_SECONDS = 300.0


@dataclass
class PendingConfirmation:
    """A confirmation request awaiting the admin's YES/NO — NOT an approval.

    An approval exists only after the admin says YES, when the gateway
    calls ``gate.grant`` for the exact (tool, arguments) pair.
    """

    request_id: str
    tool_name: str
    arguments: Dict[str, Any]
    chat_id: str
    created_at: float
    expires_at: float


class TelegramGateway:
    """Route Telegram messages to an existing agent with gated approvals.

    Parameters
    ----------
    channel:
        A :class:`~openjarvis.channels.telegram.TelegramChannel` (or any
        ``BaseChannel``-compatible object with ``on_message`` / ``send`` /
        ``connect`` / ``disconnect``). The channel owns the bot token.
    agent:
        The existing agent to route messages to: a plain callable
        ``f(text) -> str | object with .content``, an object with
        ``run(text)``, or an object with ``ask(text)`` returning a dict
        with a ``"content"`` key (e.g. ``JarvisSystem``).
    confirmation_gate:
        The shared central gate. If omitted, a private gate is created —
        callers that want Telegram approvals to reach the agent's
        ``ToolExecutor`` MUST pass the same instance the executor uses.
    allowed_chat_ids:
        Comma-separated admin chat ids. If empty, the channel's own
        ``_allowed_chat_ids`` is used. Confirmations are refused unless
        the effective allowlist is non-empty.
    confirmation_ttl_seconds:
        How long a pending confirmation (and the grant made from a YES)
        lives before it expires unapproved / unusable.
    max_workers:
        Background pool size for ``on_message`` dispatch so a slow agent
        run never blocks the channel's polling loop.
    """

    def __init__(
        self,
        channel: Any,
        agent: Any,
        *,
        confirmation_gate: Optional[ConfirmationGate] = None,
        allowed_chat_ids: str = "",
        confirmation_ttl_seconds: float = _DEFAULT_CONFIRMATION_TTL_SECONDS,
        max_workers: int = 2,
    ) -> None:
        self._channel = channel
        self._agent = agent
        self._gate = confirmation_gate or ConfirmationGate()
        self._allowed_chat_ids = allowed_chat_ids
        if float(confirmation_ttl_seconds) <= 0:
            raise ValueError("confirmation_ttl_seconds must be positive")
        self._confirmation_ttl = float(confirmation_ttl_seconds)
        self._pending: Dict[str, PendingConfirmation] = {}
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._resolve_reply = self._build_resolver(agent)

    # -- wiring ---------------------------------------------------------------

    def attach(self) -> "TelegramGateway":
        """Register this gateway as the channel's message handler."""
        self._channel.on_message(self._on_channel_message)
        return self

    def start(self) -> None:
        """Connect the underlying channel (starts Bot API long polling)."""
        self._channel.connect()

    def stop(self) -> None:
        """Disconnect the underlying channel."""
        self._channel.disconnect()

    def shutdown(self, *, wait: bool = True) -> None:
        """Shut down the background dispatch pool."""
        self._pool.shutdown(wait=wait)

    def _on_channel_message(self, msg: ChannelMessage) -> None:
        self._pool.submit(self.handle_message, msg)

    # -- agent resolution ------------------------------------------------------

    @staticmethod
    def _build_resolver(agent: Any) -> Callable[[str], str]:
        """Return ``text -> reply`` for the supported agent shapes."""
        if callable(agent):

            def _call(text: str) -> str:
                return _coerce_reply(agent(text))

            return _call
        if hasattr(agent, "run") and callable(getattr(agent, "run")):

            def _run(text: str) -> str:
                return _coerce_reply(agent.run(text))

            return _run
        if hasattr(agent, "ask") and callable(getattr(agent, "ask")):

            def _ask(text: str) -> str:
                result = agent.ask(text)
                if isinstance(result, dict):
                    return str(result.get("content", ""))
                return _coerce_reply(result)

            return _ask
        raise TypeError(
            "TelegramGateway agent must be a callable, or expose run() or ask()"
        )

    # -- allowlist -------------------------------------------------------------

    def _effective_allowlist(self) -> List[str]:
        raw = self._allowed_chat_ids or getattr(self._channel, "_allowed_chat_ids", "")
        return [cid.strip() for cid in str(raw).split(",") if cid.strip()]

    # -- confirmations ----------------------------------------------------------

    def purge_expired(self) -> int:
        """Drop expired pending confirmations. Returns the number removed."""
        now = time.time()
        expired = [rid for rid, p in self._pending.items() if p.expires_at <= now]
        for rid in expired:
            del self._pending[rid]
        return len(expired)

    def list_pending(self) -> List[Dict[str, Any]]:
        """Pending confirmations, WITHOUT arguments (they may hold secrets)."""
        self.purge_expired()
        return [
            {
                "request_id": p.request_id,
                "tool_name": p.tool_name,
                "chat_id": p.chat_id,
                "expires_at": p.expires_at,
            }
            for p in self._pending.values()
        ]

    def request_confirmation(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        chat_id: str,
        *,
        message_id: str = "",
    ) -> str:
        """Ask the admin chat to approve ONE exact (tool, arguments) action.

        Registers a pending request (not an approval) and sends the admin
        a prompt with redacted arguments. The admin's ``YES <id>`` reply
        grants a single-use approval via the central gate; ``NO <id>``
        grants nothing. Raises ``ValueError`` when confirmations are not
        admin-only (empty allowlist, chat not allowlisted, bad tool/args)
        and ``RuntimeError`` if the prompt itself could not be delivered
        — in that case no pending request is left behind, so a later
        ``YES`` cannot approve an action the admin never saw requested.
        """
        if not tool_name or not isinstance(tool_name, str):
            raise ValueError("confirmation tool_name must be a non-empty string")
        if not isinstance(arguments, dict):
            raise ValueError("confirmation arguments must be a JSON object")
        # Fail fast on non-serializable arguments (same check the gate uses).
        canonical_arguments(arguments)
        allowlist = self._effective_allowlist()
        if not allowlist:
            raise ValueError(
                "Telegram confirmations require a non-empty allowed_chat_ids "
                "admin allowlist; an empty allowlist is not admin-only, so "
                "no approval can be requested or granted via Telegram."
            )
        if str(chat_id) not in allowlist:
            raise ValueError("confirmation chat_id is not in the admin allowlist")

        self.purge_expired()
        now = time.time()
        request_id = secrets.token_hex(8)
        pending = PendingConfirmation(
            request_id=request_id,
            tool_name=tool_name,
            arguments=dict(arguments),
            chat_id=str(chat_id),
            created_at=now,
            expires_at=now + self._confirmation_ttl,
        )
        self._pending[request_id] = pending

        redacted_args = redact_value(arguments)
        try:
            args_text = json.dumps(redacted_args, sort_keys=True, default=str)
        except (TypeError, ValueError):
            args_text = "[REDACTED: unscannable value]"
        prompt = (
            f"Approval requested (request {request_id}):\n"
            f"Tool: {tool_name}\n"
            f"Arguments: {args_text}\n"
            f'Reply "YES {request_id}" to approve this exact action once, '
            f'or "NO {request_id}" to deny.\n'
            f"This request expires in {int(self._confirmation_ttl)} seconds."
        )
        try:
            delivered = self._channel.send(str(chat_id), prompt)
        except Exception:
            delivered = False
        if not delivered:
            # The admin never saw the request: leave no pending approval
            # path behind. Fail closed.
            self._pending.pop(request_id, None)
            raise RuntimeError(
                "Telegram confirmation prompt could not be delivered; "
                "no approval was requested."
            )
        logger.debug(
            "Telegram confirmation requested: tool=%s request_id=%s",
            tool_name,
            request_id,
        )
        return request_id

    def _try_handle_confirmation(self, msg: ChannelMessage) -> Optional[str]:
        """Handle a YES/NO confirmation reply. Returns the reply, or None
        if *msg* is not a confirmation reply for this chat."""
        match = _CONFIRM_RE.match(msg.content.strip())
        if match is None:
            return None
        verdict, request_id = match.group(1).upper(), match.group(2)
        self.purge_expired()
        pending = self._pending.get(request_id)
        if pending is None:
            # Unknown / expired id: not a confirmation — fall through to
            # the agent so ordinary chat ("YES 123") still works.
            return None
        if pending.chat_id != msg.conversation_id:
            # A YES from any other chat must never approve. Fall through
            # silently (no existence leak) instead of granting.
            return None
        if not self._effective_allowlist():
            # Allowlist vanished: never grant. Fall through.
            return None
        # First use consumes the pending entry, so a replayed YES grants
        # nothing.
        del self._pending[request_id]
        if verdict == "NO":
            logger.debug(
                "Telegram confirmation denied: tool=%s request_id=%s",
                pending.tool_name,
                request_id,
            )
            return (
                f"Denied: {pending.tool_name} (request {request_id}). "
                "No approval was granted."
            )
        # YES: mint the single-use, exact-arguments approval in the
        # central gate. The ToolExecutor consumes it once via
        # consume_matching for exactly this tool + arguments, or it
        # expires. The gate token is never sent over Telegram.
        remaining = max(1.0, pending.expires_at - time.time())
        self._gate.grant(pending.tool_name, pending.arguments, ttl_seconds=remaining)
        logger.debug(
            "Telegram confirmation approved: tool=%s request_id=%s",
            pending.tool_name,
            request_id,
        )
        return (
            f"Approved: {pending.tool_name} (request {request_id}). "
            "The action will run once with exactly these arguments."
        )

    # -- inbound routing ---------------------------------------------------------

    def handle_message(self, msg: ChannelMessage) -> Optional[str]:
        """Route one inbound Telegram message to the agent and reply.

        Returns the (redacted) reply text sent, or ``None`` when nothing
        was sent (dropped chat, empty reply, or a send failure). Never
        logs message content, arguments, or tokens.
        """
        if getattr(msg, "channel", "telegram") != "telegram":
            return None
        confirmation_reply = self._try_handle_confirmation(msg)
        if confirmation_reply is not None:
            confirmation_reply = redact_text(confirmation_reply)
            self._send_reply(msg, confirmation_reply)
            return confirmation_reply

        # Defense in depth: the channel already drops unlisted chats, but
        # never route an unlisted chat to the agent even if it reaches us.
        allowlist = self._effective_allowlist()
        if allowlist and msg.conversation_id not in allowlist:
            return None

        try:
            reply = self._resolve_reply(msg.content)
        except Exception:
            # Fixed generic text only — exception text (which may carry
            # secrets or paths) never reaches Telegram.
            reply = safe_error_message("chat")
        if not reply:
            return None
        redacted = redact_text(reply)
        if not redacted:
            return None
        self._send_reply(msg, redacted)
        return redacted

    def _send_reply(self, msg: ChannelMessage, text: str) -> None:
        try:
            delivered = self._channel.send(
                msg.conversation_id,
                text,
                conversation_id=getattr(msg, "message_id", ""),
            )
        except Exception:
            logger.debug("Telegram gateway send failed", exc_info=True)
            return
        if not delivered:
            logger.debug("Telegram gateway send returned False")


def _coerce_reply(result: Any) -> str:
    if isinstance(result, str):
        return result
    content = getattr(result, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(result, dict):
        return str(result.get("content", ""))
    return str(result)


__all__ = ["PendingConfirmation", "TelegramGateway"]
