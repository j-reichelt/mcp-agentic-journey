# mcp-agentic-journey
A journey into understanding the concepts behind MCP and how to implement it into a useable Agentic AI assistant. 

The goal is to build an assistant that interface with local machine (files, notes), with the potential to migrate to a cloud service, and integrate third-party open-source MCP servers to expand capabilities.

---
## Architecture Blueprint

'''mermaid
graph TD
    User([User Prompt]) --> Client[Agentic Client Loop / Brain]
    Client --> |1. Context & Routing | LLM[LLM: Ollama / Claude]
    LLM --> |2. Tool Call Request | Client
    Client --> | 3. JSON-RPC via Stdio | MCPServer[Wodan]
    MCPServer --> | 4. Read/Write | LocalData[(Mock Local Data/Files)]
    MCPServer --> | 5. Execution Result | Client
    Client --> | 6. Final Answer | User
'''

---
