"""Phase 1 smoke test: connect to the notes server and exercise each primitive.

This is NOT the Phase 2 agent loop (no LLM here). It is a hand-written client
that proves the server works end to end over stdio:

    list tools -> call a tool -> read a resource -> get a prompt

Run it after installing dependencies (see READMEV2.md):

    python client/smoke_test.py

It launches ``servers/notes_server/server.py`` as a subprocess, so no server
needs to be running beforehand.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

# Path to the server script, resolved relative to this file so the test works
# from any working directory.
SERVER = Path(__file__).resolve().parent.parent / "servers" / "notes_server" / "server.py"


def _text(result) -> str:
    """Pull plain text out of a result's content blocks.

    Tool results expose ``.content``; resource reads expose ``.contents``.
    """
    blocks = getattr(result, "content", None) or getattr(result, "contents", None) or []
    return "\n".join(getattr(block, "text", str(block)) for block in blocks)


async def main() -> int:
    # Launch the server as a subprocess over stdio, using this same Python
    # interpreter so it finds the installed mcp package.
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])

    async with Client(params) as client:
        print("Connected to:", client.server_info.name if client.server_info else "?")

        # 1. Discover tools.
        tools = await client.list_tools()
        print("\nTools:")
        for tool in tools.tools:
            print(f"  - {tool.name}: {tool.description or ''}".rstrip())

        # 2. Call the add tool (the canonical round-trip check).
        add_result = await client.call_tool("add", {"a": 2, "b": 3})
        print("\nadd(2, 3) ->", _text(add_result))

        # 3. Call list_notes, then read the first note.
        notes_result = await client.call_tool("list_notes")
        print("list_notes ->", _text(notes_result))

        read_result = await client.call_tool("read_note", {"name": "welcome.md"})
        print("\nread_note('welcome.md') ->")
        print(_text(read_result))

        # 4. Read the welcome resource.
        resource = await client.read_resource("notes://welcome")
        print("\nresource notes://welcome ->")
        print(_text(resource))

        # 5. List prompts.
        prompts = await client.list_prompts()
        print("\nPrompts:", [p.name for p in prompts.prompts])

    print("\nSmoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
