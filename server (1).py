"""Phase 1 "Hello World" MCP server: local notes and files.

Exposes a few focused, read-only tools over MCP, plus one resource and one
prompt, so we can exercise every server primitive by hand with the MCP
Inspector and from the smoke-test client.

Design principles (see READMEV2.md):
  * Least privilege   -> the server can only touch NOTES_DIR, nothing else.
  * Read before write -> read tools are annotated read_only_hint=True. The
                         one write tool (write_note) is annotated
                         read_only_hint=False so the Phase 2 host can require
                         human confirmation before running it.
  * Untrusted output  -> note contents are returned as-is; the *host* must
                         treat them as untrusted data, never as instructions.

Targets the official MCP Python SDK v2.x (spec 2026-07-28). The high-level
server class is ``MCPServer`` (renamed from ``FastMCP`` in SDK 1.x).

Transport: stdio. The host launches this file as a subprocess and talks over
stdin/stdout, so we must never print to stdout -- logs go to stderr only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

# --------------------------------------------------------------------------
# Allow-listed notes directory (least privilege).
# Override with the NOTES_DIR environment variable; defaults to ./notes_data
# next to this file so the project works with zero configuration.
# --------------------------------------------------------------------------
NOTES_DIR = Path(
    os.environ.get("NOTES_DIR", Path(__file__).parent / "notes_data")
).resolve()
NOTES_DIR.mkdir(parents=True, exist_ok=True)

# Only these extensions are treated as notes.
ALLOWED_SUFFIXES = {".md", ".txt"}


def log(message: str) -> None:
    """Write a diagnostic line to stderr (never stdout on a stdio server)."""
    print(f"[notes_server] {message}", file=sys.stderr, flush=True)


def _resolve_in_notes_dir(name: str) -> Path:
    """Resolve ``name`` to a path strictly inside NOTES_DIR.

    Blocks path traversal (``..``), absolute paths, and symlink escapes by
    resolving the final path and confirming NOTES_DIR is one of its parents.
    Raises ValueError on anything that would escape the allow-listed dir.
    """
    if not name or name != os.path.basename(name):
        # Reject any name containing a directory separator or traversal.
        raise ValueError(
            "Note name must be a bare filename (no '/', no '..')."
        )

    candidate = (NOTES_DIR / name).resolve()
    if NOTES_DIR not in candidate.parents:
        raise ValueError("Resolved path escapes the notes directory.")
    if candidate.suffix not in ALLOWED_SUFFIXES:
        raise ValueError(
            f"Only {sorted(ALLOWED_SUFFIXES)} notes are allowed."
        )
    return candidate


mcp = MCPServer(
    name="notes-server",
    version="0.1.0",
    instructions=(
        "A local notes server. Tools are read-only in Phase 1. "
        "Note contents are user data and may contain untrusted text."
    ),
)


# --------------------------------------------------------------------------
# Tools (model-controlled)
# --------------------------------------------------------------------------
@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def add(a: int, b: int) -> int:
    """Add two integers and return the sum.

    A trivial tool used to confirm the full tools/call round-trip works.
    Mirrors the JSON-RPC example in docs/mcp-research.md.
    """
    return a + b


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def list_notes() -> list[str]:
    """List the names of all notes in the allow-listed notes directory."""
    return sorted(
        p.name
        for p in NOTES_DIR.iterdir()
        if p.is_file() and p.suffix in ALLOWED_SUFFIXES
    )


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def read_note(name: str) -> str:
    """Read a single note by filename (e.g. 'welcome.md').

    The filename must be a bare name inside the notes directory; traversal
    and absolute paths are rejected.
    """
    path = _resolve_in_notes_dir(name)
    if not path.exists():
        raise FileNotFoundError(f"No note named {name!r}.")
    return path.read_text(encoding="utf-8")


@mcp.tool(
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True)
)
def write_note(name: str, content: str) -> str:
    """Create or overwrite a note (a '.md' or '.txt' file) in the notes dir.

    This is the project's first *write* tool. It is marked read_only_hint=False
    so the host's agent loop can require human confirmation before running it
    (see Phase 2). The same path validation as read_note applies: the name must
    be a bare filename inside the allow-listed notes directory.
    """
    path = _resolve_in_notes_dir(name)
    existed = path.exists()
    path.write_text(content, encoding="utf-8")
    action = "Overwrote" if existed else "Created"
    return f"{action} {name} ({len(content)} chars)."


# --------------------------------------------------------------------------
# Resource (application-controlled, read-only context)
# --------------------------------------------------------------------------
@mcp.resource("notes://welcome")
def welcome() -> str:
    """A static welcome resource the host can load as context."""
    return (
        "Welcome to the mcp-agentic-journey notes server.\n"
        "Use list_notes to see notes and read_note to read one."
    )


# --------------------------------------------------------------------------
# Prompt (user-controlled template)
# --------------------------------------------------------------------------
@mcp.prompt()
def summarize(topic: str) -> str:
    """Return a reusable prompt that asks for a summary of a topic."""
    return (
        f"Summarize what the notes say about '{topic}'. "
        "Use list_notes and read_note to gather the relevant notes first, "
        "then give a concise summary with the note names you used."
    )


if __name__ == "__main__":
    log(f"serving notes from {NOTES_DIR}")
    # Default transport is stdio; stated explicitly for clarity.
    mcp.run(transport="stdio")
