"""Phase 1: persisted-store redaction.

Agent output and derived records are redacted fail-closed at write time
in the trace store, the managed-agent DB, and the channel session
store. A stored record must never contain a raw secret the model
emitted. Tests use synthetic secrets only.

Boundary (documented, tested): live user input channels are NOT
redacted at write — the agent reads them to act on (user_to_agent
queue, task description, user-role session history). Operational
config (config_json) is NOT redacted — it may hold credentials needed
to connect; the vault is the channel for credentials.
"""

from __future__ import annotations

import time
from pathlib import Path

from openjarvis.agents.manager import AgentManager
from openjarvis.core.types import StepType, Trace, TraceStep
from openjarvis.server.session_store import SessionStore
from openjarvis.traces.store import TraceStore

# Synthetic secrets matching the scanner patterns. Never real.
_FAKE_OPENAI_KEY = "sk-" + "A" * 32
_FAKE_PASSWORD_ASSIGN = 'password = "synthetic-password-1234"'
_FAKE_API_KEY_ASSIGN = 'api_key = "synthetic-api-value-9876"'
_RAW_SECRETS = (
    _FAKE_OPENAI_KEY,
    "synthetic-password-1234",
    "synthetic-api-value-9876",
)


def _assert_no_raw_secret(text: str) -> None:
    for raw in _RAW_SECRETS:
        assert raw not in text, f"raw secret leaked: {raw[:12]}..."


class TestTraceStoreRedaction:
    def test_trace_save_redacts_result_query_messages_steps(self, tmp_path: Path):
        store = TraceStore(str(tmp_path / "traces.db"))
        now = time.time()
        trace = Trace(
            query=f"what is {_FAKE_PASSWORD_ASSIGN}?",
            agent="orchestrator",
            model="qwen3:8b",
            engine="ollama",
            result=f"here is the key: {_FAKE_OPENAI_KEY}",
            outcome="success",
            started_at=now,
            ended_at=now + 1.0,
            total_tokens=10,
            total_latency_seconds=0.5,
            metadata={"note": _FAKE_API_KEY_ASSIGN},
            messages=[{"role": "assistant", "content": _FAKE_OPENAI_KEY}],
            steps=[
                TraceStep(
                    step_type=StepType.TOOL_CALL,
                    timestamp=now,
                    duration_seconds=0.1,
                    input={"args": _FAKE_PASSWORD_ASSIGN},
                    output={"result": _FAKE_OPENAI_KEY},
                    metadata={"x": _FAKE_API_KEY_ASSIGN},
                )
            ],
        )
        store.save(trace)
        got = store.get(trace.trace_id)
        assert got is not None
        # Stored copy redacted everywhere.
        _assert_no_raw_secret(got.query)
        _assert_no_raw_secret(got.result)
        _assert_no_raw_secret(str(got.metadata))
        _assert_no_raw_secret(str(got.messages))
        for step in got.steps:
            _assert_no_raw_secret(str(step.input))
            _assert_no_raw_secret(str(step.output))
            _assert_no_raw_secret(str(step.metadata))
        # Redaction markers present (not silently dropped).
        assert "REDACTED" in got.result
        # In-memory trace object NOT mutated by save().
        assert _FAKE_OPENAI_KEY in trace.result
        store.close()

    def test_trace_save_redacts_query(self, tmp_path: Path):
        store = TraceStore(str(tmp_path / "traces.db"))
        trace = Trace(query=_FAKE_PASSWORD_ASSIGN, result="ok")
        store.save(trace)
        got = store.get(trace.trace_id)
        assert got is not None
        _assert_no_raw_secret(got.query)
        store.close()


class TestManagerRedaction:
    def test_store_agent_response_redacted(self, tmp_path: Path):
        mgr = AgentManager(str(tmp_path / "agents.db"))
        agent = mgr.create_agent("redact-test")
        mgr.store_agent_response(
            agent["id"],
            f"the key is {_FAKE_OPENAI_KEY}",
            tool_calls=[{"tool": "x", "arguments": _FAKE_PASSWORD_ASSIGN}],
        )
        msgs = mgr.list_messages(agent["id"])
        assert len(msgs) == 1
        _assert_no_raw_secret(msgs[0]["content"])
        _assert_no_raw_secret(str(msgs[0]["tool_calls"]))
        assert "REDACTED" in msgs[0]["content"]
        mgr.close()

    def test_add_agent_response_redacted(self, tmp_path: Path):
        mgr = AgentManager(str(tmp_path / "agents.db"))
        agent = mgr.create_agent("redact-test")
        mgr.add_agent_response(agent["id"], _FAKE_API_KEY_ASSIGN)
        msgs = mgr.list_messages(agent["id"])
        _assert_no_raw_secret(msgs[0]["content"])
        mgr.close()

    def test_learning_log_redacted(self, tmp_path: Path):
        mgr = AgentManager(str(tmp_path / "agents.db"))
        agent = mgr.create_agent("redact-test")
        mgr.add_learning_log(
            agent["id"],
            "tool_result",
            f"got {_FAKE_OPENAI_KEY}",
            {"arguments": _FAKE_PASSWORD_ASSIGN},
        )
        logs = mgr.list_learning_log(agent["id"])
        assert len(logs) == 1
        _assert_no_raw_secret(logs[0]["description"])
        _assert_no_raw_secret(str(logs[0]["data"]))
        mgr.close()

    def test_checkpoint_redacted(self, tmp_path: Path):
        mgr = AgentManager(str(tmp_path / "agents.db"))
        agent = mgr.create_agent("redact-test")
        mgr.save_checkpoint(
            agent["id"],
            "tick-1",
            {"messages": [{"role": "assistant", "content": _FAKE_OPENAI_KEY}]},
            {"tool_args": _FAKE_PASSWORD_ASSIGN},
        )
        cps = mgr.list_checkpoints(agent["id"])
        assert len(cps) == 1
        _assert_no_raw_secret(str(cps[0]))
        mgr.close()

    def test_summary_memory_redacted(self, tmp_path: Path):
        mgr = AgentManager(str(tmp_path / "agents.db"))
        agent = mgr.create_agent("redact-test")
        mgr.update_summary_memory(agent["id"], f"summary with {_FAKE_OPENAI_KEY}")
        got = mgr.get_agent(agent["id"])
        assert got is not None
        _assert_no_raw_secret(got["summary_memory"])
        mgr.close()

    def test_task_findings_redacted(self, tmp_path: Path):
        mgr = AgentManager(str(tmp_path / "agents.db"))
        agent = mgr.create_agent("redact-test")
        task = mgr.create_task(agent["id"], "plain task description")
        mgr.update_task(
            task["id"],
            progress={"note": _FAKE_OPENAI_KEY},
            findings=[{"finding": _FAKE_PASSWORD_ASSIGN}],
        )
        tasks = mgr.list_tasks(agent["id"])
        assert len(tasks) == 1
        _assert_no_raw_secret(str(tasks[0]["progress"]))
        _assert_no_raw_secret(str(tasks[0]["findings"]))
        mgr.close()

    def test_user_input_not_redacted_boundary(self, tmp_path: Path):
        """Boundary: user_to_agent queue is live input — stored as written.

        The agent reads this queue to act on. Redacting at write would
        strip user-provided data before the agent sees it. Users must
        not paste secrets they do not want stored.
        """
        mgr = AgentManager(str(tmp_path / "agents.db"))
        agent = mgr.create_agent("redact-test")
        mgr.send_message(agent["id"], f"my key is {_FAKE_OPENAI_KEY}")
        pending = mgr.get_pending_messages(agent["id"])
        assert len(pending) == 1
        # Deliberately NOT redacted — documented boundary.
        assert _FAKE_OPENAI_KEY in pending[0]["content"]
        mgr.close()


class TestSessionStoreRedaction:
    def test_assistant_message_redacted_user_message_kept(self, tmp_path: Path):
        store = SessionStore(str(tmp_path / "sessions.db"))
        store.get_or_create("sender-1", "telegram")
        store.append_message(
            "sender-1", "telegram", "assistant", f"key {_FAKE_OPENAI_KEY}"
        )
        store.append_message(
            "sender-1", "telegram", "user", f"my key is {_FAKE_OPENAI_KEY}"
        )
        sess = store.get_or_create("sender-1", "telegram")
        history = sess["conversation_history"]
        assert len(history) == 2
        # Assistant (model) output redacted.
        _assert_no_raw_secret(history[0]["content"])
        assert history[0]["role"] == "assistant"
        # User input stored as written (boundary).
        assert _FAKE_OPENAI_KEY in history[1]["content"]
        assert history[1]["role"] == "user"
        store.close()

    def test_pending_response_redacted(self, tmp_path: Path):
        store = SessionStore(str(tmp_path / "sessions.db"))
        store.get_or_create("sender-1", "telegram")
        store.set_pending_response("sender-1", "telegram", f"here: {_FAKE_OPENAI_KEY}")
        sess = store.get_or_create("sender-1", "telegram")
        assert sess["pending_response"] is not None
        _assert_no_raw_secret(sess["pending_response"])
        store.close()
