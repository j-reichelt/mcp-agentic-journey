mcp-agentic-journey
A journey into understanding the concepts behind the Model Context Protocol (MCP) and how to implement it in a usable agentic AI assistant.
Goal: build an assistant that interfaces with the local machine (files, notes), with the option to migrate to a cloud service and to integrate third-party open-source MCP servers to expand its capabilities.
> 📚 Background reading lives in [`docs/mcp-research.md`](docs/mcp-research.md): what MCP is, why it exists, how it works, and how it is used.
---
Architecture Blueprint
```
┌──────────────────────── HOST (our assistant app) ────────────────────────┐
│                                                                          │
│   LLM (Claude API / Ollama)  ◄──►  Agent loop  ◄──►  MCP Client(s)       │
│                                                         │        │       │
└─────────────────────────────────────────────────────────┼────────┼───────┘
                                          stdio / HTTP    │        │
                                              ┌───────────▼──┐  ┌──▼───────────────┐
                                              │ Notes/Files  │  │ 3rd-party server │
                                              │ MCP server   │  │ (e.g. web search)│
                                              │ (we build)   │  │ (open source)    │
                                              └──────────────┘  └──────────────────┘
```
Tech Stack & Frameworks
Layer	Choice	Notes
Language	Python 3.11+	
Package manager	`uv`	
MCP server framework	Official MCP Python SDK (`mcp`), `MCPServer` class	Called `FastMCP` in SDK 1.x; renamed `MCPServer` in SDK 2.x. See the note below.
MCP client	Official SDK `Client` (Phase 2), then compare with LangChain / CrewAI adapters	Write the loop by hand first so we understand it, then evaluate frameworks.
LLM	TBD (record the decision in the Journey Log)	Candidates: Anthropic Claude API, or Ollama with a local model (e.g. Llama 3.2)
Dev/debug tool	MCP Inspector (launched via `mcp dev`)	Requires Node.js
> **Note on "FastMCP":** the name refers to two different things.
> 1. The high-level server API *inside* the official SDK. This was `mcp.server.fastmcp.FastMCP` in SDK 1.x and is `mcp.server.mcpserver.MCPServer` in SDK 2.x.
> 2. A separate, community-maintained package (`fastmcp`, docs at gofastmcp.com) that builds on top of the official SDK.
>
> This project uses **only the official SDK** (`mcp`) to keep the learning path unambiguous. Many tutorials online still show the old `FastMCP` import, so expect to translate. Do not install both `mcp` and `fastmcp` unless we are deliberately comparing them.
---
Journey Log & Milestones
Phase 1: Conceptual Foundations & Hello World MCP
Goal: Understand MCP's building blocks (tools, resources, prompts) and set up a standalone server.
Status: In progress
Checklist:
[x] Initialize this GitHub repository with environment isolation
[ ] Read the MCP architecture overview (host / client / server) and summarize it in `docs/mcp-research.md`
[ ] Build the hello-world server (see Hello World)
[ ] Inspect it with MCP Inspector and call each primitive by hand
[ ] Capture one raw JSON-RPC exchange (e.g. a `tools/call`) and annotate it
What was done:
Initialized the repository with environment isolation.
Researching the difference between MCP clients and servers.
Blockers & Breakthroughs:
(Log any difficult setup steps or JSON-RPC confusion here.)
Phase 2: The Agentic Client Loop (The Brain)
Goal: Write the client loop that allows an LLM to autonomously discover and execute custom server tools.
Status: Upcoming
Planned steps:
[ ] Connect to the Phase 1 server using the SDK `Client`
[ ] Convert MCP tool definitions into the LLM provider's tool-calling format
[ ] Implement the loop: prompt → model requests tool → client calls tool via MCP → result back to model → repeat until a final answer
[ ] Add guardrails: max iterations, error handling, human confirmation for write operations
[ ] Decide LLM (Claude API vs Ollama) and record why
Phase 3: Multi-Server Integration & Expansion
Goal: Configure the AI assistant to connect to multiple MCP servers simultaneously (combining a local notes tool with an open-source web search server).
Status: Upcoming
Planned steps:
[ ] Run two servers at once and namespace their tools to avoid name collisions
[ ] Evaluate one open-source server for trustworthiness before installing (source, maintainers, permissions)
[ ] Compare our hand-written loop with LangChain / CrewAI MCP adapters
Phase 4: Cloud Hosting (Stretch)
Goal: Run the server remotely over Streamable HTTP.
Status: Upcoming
Planned steps:
[ ] Switch the server from stdio to Streamable HTTP
[ ] Add authentication (the spec builds on OAuth 2.x)
[ ] Containerize and deploy to a cloud service
Dated Entries
(Newest first. One short entry per working session is plenty for supervision meetings.)
2026-10-06: Tutorials and current SDK disagree
Discovered that the MCP specification and the Python SDK both had major releases on 2026-07-28 (stateless protocol, `FastMCP` renamed `MCPServer`). Many tutorials predate this.
Decision: target the current spec and SDK 2.x; treat older tutorials as conceptual guides only.
Open question for supervisor: how much time to spend on the legacy session-based protocol, given most existing tutorials describe it?
---
Running This Project Locally
1. Prerequisites
Python 3.11+
`uv`: a fast Python project and package manager that replaces `pip` + `venv` for most workflows. Install instructions: https://docs.astral.sh/uv/
Node.js (for `npx`): `mcp dev` launches the MCP Inspector, which is a Node tool
An LLM API key (Phase 2 onward), if using a hosted model
2. Installation
```bash
# Clone the repository
git clone https://github.com/<your-username>/<name_of_repo>.git
cd <name_of_repo>

# Create the project, virtual environment, and install dependencies
uv init            # skip if pyproject.toml already exists
uv add "mcp[cli]"  # quotes matter in zsh
```
`uv add` creates `.venv/` automatically. You can either prefix commands with `uv run` (recommended, no activation needed) or activate manually:
```bash
source .venv/bin/activate       # macOS / Linux
.venv\Scripts\activate          # Windows
```
Verify the install:
```bash
uv run mcp version
```
3. Suggested Repository Layout
```
mcp-agentic-journey/
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example            # template only; never commit real keys
├── docs/
│   └── mcp-research.md
├── servers/
│   └── notes_server/
│       └── server.py       # our custom MCP server
└── client/
    └── agent.py            # Phase 2: the agentic loop
```
Minimal `.gitignore`:
```
.venv/
__pycache__/
.env
```
4. Hello World Server
Create `servers/notes_server/server.py`:
```python
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("notes-server")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@mcp.resource("notes://welcome")
def welcome() -> str:
    """A static resource the client can read."""
    return "Hello from the notes server!"


@mcp.prompt()
def summarize(text: str) -> str:
    """Reusable prompt template."""
    return f"Summarize the following in 3 bullet points:\n\n{text}"


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
```
The three decorators map to MCP's three server primitives:
Primitive	Who controls it	Example here
Tool	The model decides when to call it	`add`
Resource	The application decides what to load	`notes://welcome`
Prompt	The user picks it	`summarize`
> Docstrings and type hints are not decoration: the SDK turns them into the tool description and JSON Schema that the LLM sees. Write them for the model.
5. Testing the MCP Server
Without booting up the entire AI client, interactively test the custom server tools:
```bash
uv run mcp dev servers/notes_server/server.py
```
This opens the MCP Inspector in the browser, where you can list tools, resources and prompts, call them with test arguments, and watch the raw JSON-RPC messages.
Scripted smoke test (no browser needed). Save as `client/smoke_test.py`:
```python
import asyncio
from mcp import Client, StdioServerParameters


async def main():
    params = StdioServerParameters(
        command="python", args=["servers/notes_server/server.py"]
    )
    async with Client(params) as client:
        tools = await client.list_tools()
        print("tools:", [t.name for t in tools.tools])

        result = await client.call_tool("add", {"a": 2, "b": 3})
        print("add(2, 3):", result.content[0].text)

        resource = await client.read_resource("notes://welcome")
        print("resource:", resource.contents[0].text)


asyncio.run(main())
```
```bash
uv run python client/smoke_test.py
```
Expected output:
```
tools: ['add']
add(2, 3): 5
resource: Hello from the notes server!
```
6. Environment Variables (Phase 2+)
Copy `.env.example` to `.env` and fill in values. Never commit `.env`.
```
ANTHROPIC_API_KEY=
# OLLAMA_HOST=http://localhost:11434
```
7. Troubleshooting
Symptom	Likely cause
`ModuleNotFoundError: mcp.server.fastmcp`	Code or tutorial written for SDK 1.x. Use `mcp.server.mcpserver.MCPServer`, or pin `mcp>=1.28,<2` to follow a 1.x tutorial exactly.
`mcp dev` fails to start the Inspector	Node.js / `npx` not installed or not on `PATH`.
`zsh: no matches found: mcp[cli]`	Quote the extra: `"mcp[cli]"`.
Server prints break the client (stdio)	Never `print()` to stdout in a stdio server; stdout carries the protocol. Log to stderr.
---
Design Principles
Least privilege. The notes/files server should only be able to touch an explicitly allow-listed directory, with path-traversal checks.
Read before write. Start with read-only tools; add write/delete tools later, behind confirmation.
Treat tool output as untrusted input. Text returned by a tool (especially from third-party servers) can contain instructions aimed at the model.
Understand before adopting. Read the source of any third-party server before connecting it to a machine that holds personal files.
---
References
MCP specification (current revision 2026-07-28): https://modelcontextprotocol.io/specification/2026-07-28
MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
Project research notes: `docs/mcp-research.md`
