Model Context Protocol (MCP): Research Notes
Compiled 2026-10-06. MCP is evolving quickly; the spec and SDKs changed substantially in July 2026. Re-verify version-specific details before citing them.
Contents
What is MCP?
Why did it come about?
How it works
What changed in the 2026-07-28 spec
How MCP is used
MCP compared with related ideas
Security considerations
Implications for cloud hosting
Glossary
Open questions
Sources
---
1. What is MCP?
The Model Context Protocol is an open standard that lets AI applications (Claude, ChatGPT, Cursor, VS Code and others) discover and use external tools, data, and prompt templates through one common interface, rather than a custom integration for every app-and-service pair.
Key points:
It is a protocol (a specification), not a product or a library. SDKs exist in many languages, but the contract is the spec.
Messages are JSON-RPC 2.0.
The spec is versioned by date, not number. Revisions so far: `2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25`, and `2026-07-28` (current).
Created by Anthropic (released November 2024). In December 2025 Anthropic donated MCP to the Agentic AI Foundation (AAIF), a directed fund under the Linux Foundation, co-founded by Anthropic, Block, and OpenAI. Anthropic stated that MCP's maintainer and governance model continued unchanged.
A useful one-line analogy: MCP is to AI tools what USB-C is to devices: a standard port so that any compliant client can plug into any compliant server.
---
2. Why did it come about?
The N×M integration problem
Before MCP, connecting an LLM application to external systems (a database, a file system, a calendar, GitHub) meant writing bespoke glue code. With N AI applications and M services, the ecosystem needed up to N × M custom integrations, each with its own conventions for describing tools, handling auth, and formatting results.
MCP changes this to N + M: each application implements the client side once, each service implements the server side once, and they interoperate.
Models needed context and the ability to act
LLMs are limited to their training data and what is pasted into the prompt. Useful assistants need to read live data and take actions. Function calling (provider-specific tool APIs) solved part of this, but the definition and execution of those tools was still custom for each application. MCP standardizes the layer that sits around tool calling: how tools are discovered, described, invoked, and how results return.
Prior art: the Language Server Protocol
MCP's design was explicitly inspired by the Language Server Protocol (LSP), which solved the same N×M problem for code editors and programming languages. MCP applies the same idea to AI applications and their capabilities.
Adoption timeline (high level)
When	Milestone
Nov 2024	Anthropic releases MCP as an open standard
2025	Rapid adoption by other AI platforms and developer tools; new spec revisions add Streamable HTTP (2025-03-26), stronger authorization, and more
Dec 2025	Donated to the Linux Foundation's AAIF. At that point: 10,000+ active servers and 97M+ monthly SDK downloads; first-class client support across ChatGPT, Claude, Cursor, Gemini, Microsoft Copilot, VS Code and more
Jul 28, 2026	`2026-07-28` spec released: the largest revision since launch; makes the protocol stateless (see section 4). Python SDK v2 ships the same day
---
3. How it works
3.1 The three roles
Role	What it is	Example
Host	The AI application the user interacts with. It contains the LLM and manages one or more clients.	Claude Desktop, an IDE, our assistant
Client	A component inside the host that maintains the connection to one server.	The MCP `Client` in our agent code
Server	A program that exposes capabilities (tools, resources, prompts) over MCP.	Our notes server, a GitHub server, a web-search server
Important: the model never talks to a server directly. The host's client mediates every call. This is where a host can enforce permissions and ask the user for confirmation.
3.2 Two layers
Data layer: the JSON-RPC messages and the primitives (what can be asked and answered).
Transport layer: how those messages travel.
3.3 Server primitives
Primitive	Controlled by	What it is	Typical use
Tools	The model	Functions with a name, description, and JSON Schema for inputs. The model decides when to call them.	`search_issues`, `create_invoice`, `read_note`
Resources	The application	Read-only context identified by URI that the host loads.	A file, a database row, `notes://welcome`
Prompts	The user	Reusable, parameterized prompt templates the user picks.	`/summarize`, `/code-review`
Core methods you will see on the wire: `tools/list`, `tools/call`, `resources/list`, `resources/read`, `prompts/list`, `prompts/get`.
The spec says clients must treat tool annotations (hints like "read-only" or "destructive") as untrusted unless the server itself is trusted.
3.4 Transports
Transport	Used for	How
stdio	Local servers	The host launches the server as a subprocess and talks over stdin/stdout. Simple, no network. (Never write logs to stdout; use stderr.)
Streamable HTTP	Remote / cloud servers	HTTP POST requests, with optional streaming responses. Introduced in `2025-03-26`.
HTTP+SSE	Legacy	Deprecated in favor of Streamable HTTP.
3.5 Example exchange
A client asking a server to run a tool looks like this (simplified; field details vary by spec revision):
```json
// Client → Server
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": { "name": "add", "arguments": { "a": 2, "b": 3 } }
}

// Server → Client
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": { "content": [ { "type": "text", "text": "5" } ] }
}
```
3.6 The agent loop (where MCP fits)
MCP does not make an agent by itself. The agent loop lives in the host:
```
1. Client connects to servers and lists their tools
2. Host sends the user's request + tool definitions to the LLM
3. LLM replies with either a final answer OR a request to call a tool
4. If a tool call: host (optionally asks the user), then calls the tool via MCP
5. Host appends the tool result to the conversation and returns to step 2
6. Stop when the LLM gives a final answer (or a max-iteration limit is hit)
```
MCP standardizes steps 1 and 4. Steps 2, 3, 5, and 6 are the LLM provider's API and your own orchestration code. This is exactly what Phase 2 of the project builds.
---
4. What changed in the 2026-07-28 spec
This matters because most tutorials and blog posts describe the older, session-based protocol.
Major changes
Stateless protocol. The `initialize` / `initialized` handshake and the `Mcp-Session-Id` header were removed. Every request now carries its own protocol version and client capabilities in `_meta`. Servers that need state across calls use explicit server-issued handles passed as ordinary tool arguments.
`server/discover`. Servers must implement this method to advertise supported versions, capabilities, and identity.
`subscriptions/listen`. Replaces the old GET endpoint and resource subscribe/unsubscribe, giving one long-lived stream for opted-in change notifications.
Multi Round-Trip Requests (MRTR). Replaces servers sending requests to the client mid-call (for elicitation, etc.). A server instead returns an `input_required` result, and the client retries with the requested info.
Tasks (long-running operations) moved out of the core into an official extension.
No SSE stream resumability. If a stream breaks, the client re-issues the request.
Smaller changes
Cache hints (`ttlMs`, `cacheScope`) on list/read results.
Standard HTTP headers (`Mcp-Method`, `Mcp-Name`) on POST requests.
OpenTelemetry trace context conventions.
JSON Schema 2020-12 keywords allowed in tool schemas.
Authorization hardening (e.g. issuer validation per RFC 9207).
"Resource not found" error code changed to `-32602`.
Deprecated (still functional, scheduled for removal)
Roots, Sampling, and Logging client features.
HTTP+SSE transport.
OAuth Dynamic Client Registration (RFC 7591), in favor of Client ID Metadata Documents.
A formal feature-lifecycle policy now requires at least a 12-month deprecation window.
SDK impact (Python)
MCP Python SDK v2.0.0 (stable, released alongside the spec) speaks the new protocol and still serves 2025-era clients from the same server.
`FastMCP` (high-level server class) was renamed `MCPServer`; submodule path moved from `mcp.server.fastmcp` to `mcp.server.mcpserver`. The `@mcp.tool()`, `@mcp.resource()` and `@mcp.prompt()` decorators are unchanged.
Protocol types moved to a separate `mcp-types` package.
A first-class `Client` class was added.
The standalone community FastMCP package is a separate project that builds on the official SDK; its v4 tracks the SDK v2 rebuild.
---
5. How MCP is used
Everyday uses
Coding assistants connecting to repos, issue trackers, docs, and databases.
Chat assistants connecting to calendars, email, file storage, and company knowledge bases.
Automation / agent workflows chaining tools across services (e.g. read a ticket → query a database → update a document).
Local-machine integration: file systems, notes apps, and shell tools exposed via local stdio servers (this project's focus).
The ecosystem
Official and community servers: a large and growing collection, with thousands of tracked servers. Quality and trustworthiness vary widely.
Registries/directories help discover servers.
Extensions: optional protocol additions (e.g. Tasks; MCP Apps for tools that render interactive UI).
Typical build pattern (our project)
Write a server exposing a few focused tools/resources.
Test it with the MCP Inspector.
Write a host/client that gives those tools to an LLM in an agent loop.
Add more servers; the same client code handles all of them.
Move a server to Streamable HTTP to host remotely.
---
6. MCP compared with related ideas
Concept	Relationship to MCP
Function / tool calling (provider APIs)	The model-side mechanism for requesting a tool call. MCP standardizes the tool side: discovery, schemas, execution, results. An MCP client typically translates MCP tools into the provider's function-calling format.
REST APIs / OpenAPI	Designed for developers and programs. MCP wraps capabilities in a form designed for model consumption (descriptions, schemas, standardized results) and handles discovery. An MCP server often sits on top of a REST API.
RAG (retrieval-augmented generation)	A technique for injecting retrieved text into prompts. MCP can be the plumbing a RAG system uses to reach data sources, but MCP is broader (it also performs actions).
Agent frameworks (LangChain, CrewAI, etc.)	Orchestration layers. Many can act as MCP clients through adapters. MCP is the connectivity standard; frameworks provide the loop and workflow abstractions.
AGENTS.md	A convention for giving coding agents project instructions. Also hosted by AAIF, but solves a different problem.
---
7. Security considerations
MCP gives models the ability to act, which raises the stakes.
Risk	Description	Mitigation
Prompt injection via tool results	Content a tool returns (a web page, a note, an email) may contain instructions aimed at the model.	Treat tool output as untrusted data; limit what a single session can do; confirmation for sensitive actions.
Malicious or poisoned tool descriptions	A third-party server can describe its tools in ways that manipulate the model.	Vet servers; prefer well-known sources; review tool descriptions; pin versions.
Over-broad permissions	A file server with access to the whole disk.	Allow-list directories; validate paths (block `..` traversal and symlink escapes); run in a container or restricted account.
Destructive actions	Delete/write/send tools invoked autonomously.	Start read-only; require human approval for writes.
Untrusted annotations	Server-supplied hints like "read-only" can be wrong or malicious.	The spec says clients must not trust them unless the server is trusted.
Credential handling	Tokens and API keys in config files or logs.	Environment variables / secret stores; never commit `.env`; follow the spec's OAuth-based authorization for remote servers.
Supply chain	Running a community server means running someone else's code.	Read the source; check maintainers and activity; sandbox.
---
8. Implications for cloud hosting
Local → remote means transport change: stdio → Streamable HTTP.
Statelessness helps. Because the 2026-07-28 protocol has no sessions, requests are self-contained, so servers can scale horizontally behind a load balancer and fit serverless platforms more naturally. State that must persist becomes an explicit design choice (handles, databases).
Authentication becomes mandatory. A remote server must authenticate callers. The spec builds on OAuth 2.x, and the latest revision hardens it and favors Client ID Metadata Documents over Dynamic Client Registration.
Caching hints (`ttlMs`, `cacheScope`) let clients and intermediaries reduce redundant list requests.
Local-file access doesn't migrate. A cloud server can't see files on your laptop. Either keep a local server for local data and add remote servers for other capabilities (which is what Phase 3's multi-server design allows), or sync data to cloud storage.
Observability: OpenTelemetry trace propagation is documented, and the Python SDK ships tracing support.
---
9. Glossary
Term	Meaning
MCP	Model Context Protocol
Host	The AI application containing the LLM and MCP clients
Client	Per-server connection manager inside the host
Server	Program exposing tools/resources/prompts
Tool	Model-invoked function with a JSON Schema
Resource	URI-addressed read-only context
Prompt	User-selected prompt template
JSON-RPC 2.0	Lightweight request/response message format MCP uses
stdio	Local transport using standard input/output
Streamable HTTP	Remote transport using HTTP POST with optional streaming
MRTR	Multi Round-Trip Requests: how servers ask clients for more input in the stateless protocol
SEP	Spec Enhancement Proposal: the process for changing the spec
AAIF	Agentic AI Foundation (Linux Foundation) that stewards MCP
MCP Inspector	Browser tool for testing servers interactively
Elicitation	A server asking the user for additional input mid-operation
---
10. Open questions for this project
Useful discussion points for supervision meetings:
Do we target only the current stateless spec, or also study the legacy handshake/session model that most existing servers still use?
Hosted LLM (Claude API) vs. local (Ollama): what are the trade-offs for tool-calling reliability, privacy of personal notes, and cost?
When do LangChain/CrewAI add value over a ~100-line hand-written loop?
What threat model do we adopt for a local assistant with file access, and what does "human in the loop" look like in a CLI?
How should long-running work be handled now that Tasks is an extension rather than core?
---
11. Sources
Primary:
MCP specification 2026-07-28 changelog: https://modelcontextprotocol.io/specification/2026-07-28/changelog
MCP specification release page: https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28
MCP Python SDK v2.0.0 release notes: https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0
"MCP joins the Agentic AI Foundation" (Dec 9, 2025, mirrored): https://modelcontextprotocol.info/blog/joins-agentic-ai-foundation/
Secondary (explainers and news coverage):
Scalar, "What is MCP": https://scalar.com/learn/mcp/what-is-mcp
PPC Land coverage of the 2026-07-28 release: https://ppc.land/mcp-forces-ad-tech-to-rebuild-agent-servers-as-sessions-disappear/
FastMCP v4 notes (community project): https://gofastmcp.com/development/v4-notes
Suggested next step: read the architecture and base-protocol sections of the official spec directly, and cite those over secondary sources in any write-up.
