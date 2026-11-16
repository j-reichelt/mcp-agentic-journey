"""Loop-logic tests for the Phase 2 agent, with a fake LLM (no API key needed).

These drive the REAL notes MCP server over stdio but replace the Claude API
with a scripted fake, so we can check the mechanics the LLM would otherwise
trigger: MCP->Anthropic tool conversion, tool_use -> call_tool -> tool_result
threading, the max-iteration cap, and the human confirmation gate on writes.

Run:  python client/test_agent_loop.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent  # noqa: E402


def _tool_use(block_id, name, args):
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=args)


def _text(value):
    return SimpleNamespace(type="text", text=value)


class FakeMessages:
    """Replays a scripted list of responses and records requests it received."""

    def __init__(self, script):
        self._script = list(script)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self._script.pop(0)


class FakeLLM:
    def __init__(self, script):
        self.messages = FakeMessages(script)


def test_read_only_flow():
    """Model lists notes, reads one, then answers. No confirmation prompts."""
    script = [
        SimpleNamespace(content=[_tool_use("t1", "list_notes", {})], stop_reason="tool_use"),
        SimpleNamespace(
            content=[_tool_use("t2", "read_note", {"name": "welcome.md"})],
            stop_reason="tool_use",
        ),
        SimpleNamespace(content=[_text("Your notes mention project ideas.")], stop_reason="end_turn"),
    ]
    llm = FakeLLM(script)

    def no_confirm(name, args):  # must never be called for read-only tools
        raise AssertionError(f"confirmation asked for read-only tool {name}")

    answer = asyncio.run(
        agent.run_agent("what do my notes say?", llm=llm, confirm=no_confirm)
    )

    assert answer == "Your notes mention project ideas.", answer
    # The 2nd request must carry the tool_result for list_notes back to the model.
    second_request_msgs = llm.messages.requests[1]["messages"]
    tool_results = [
        blk
        for m in second_request_msgs
        if isinstance(m["content"], list)
        for blk in m["content"]
        if isinstance(blk, dict) and blk.get("type") == "tool_result"
    ]
    assert any("welcome.md" in str(tr["content"]) for tr in tool_results), tool_results
    print("PASS test_read_only_flow")


def test_write_denied(tmp_note="loop_test.md"):
    """Model tries to write; human denies; file must NOT be created."""
    note_path = Path(agent.SERVER).parent / "notes_data" / tmp_note
    if note_path.exists():
        note_path.unlink()

    script = [
        SimpleNamespace(
            content=[_tool_use("w1", "write_note", {"name": tmp_note, "content": "hi"})],
            stop_reason="tool_use",
        ),
        SimpleNamespace(content=[_text("Okay, I won't write it.")], stop_reason="end_turn"),
    ]
    llm = FakeLLM(script)
    asyncio.run(agent.run_agent("make a note", llm=llm, confirm=lambda n, a: False))

    assert not note_path.exists(), "file was written despite denial!"
    print("PASS test_write_denied")


def test_write_approved(tmp_note="loop_test.md"):
    """Model writes; human approves; file is created, then cleaned up."""
    note_path = Path(agent.SERVER).parent / "notes_data" / tmp_note
    script = [
        SimpleNamespace(
            content=[_tool_use("w1", "write_note", {"name": tmp_note, "content": "hello"})],
            stop_reason="tool_use",
        ),
        SimpleNamespace(content=[_text("Done.")], stop_reason="end_turn"),
    ]
    llm = FakeLLM(script)
    try:
        asyncio.run(agent.run_agent("make a note", llm=llm, confirm=lambda n, a: True))
        assert note_path.exists(), "approved write did not create the file"
        assert note_path.read_text() == "hello"
        print("PASS test_write_approved")
    finally:
        if note_path.exists():
            note_path.unlink()


def test_max_iterations():
    """A model that always calls a tool must stop at the iteration cap."""
    # Every response asks for a tool again; loop must terminate, not hang.
    looping = [
        SimpleNamespace(content=[_tool_use(f"t{i}", "list_notes", {})], stop_reason="tool_use")
        for i in range(5)
    ]
    llm = FakeLLM(looping)
    asyncio.run(
        agent.run_agent("loop", llm=llm, confirm=lambda n, a: True, max_iterations=3)
    )
    assert len(llm.messages.requests) == 3, len(llm.messages.requests)
    print("PASS test_max_iterations")


if __name__ == "__main__":
    test_read_only_flow()
    test_write_denied()
    test_write_approved()
    test_max_iterations()
    print("\nAll agent-loop tests passed.")
