"""
mcp_server/server.py
---------------------
MindGuard's coping-tool library exposed as a real MCP server, using the
official `mcp` Python SDK (FastMCP). This satisfies the capstone's
"MCP Server" key concept: an agent (or any MCP-compatible client, including
Claude Desktop or the ADK MCPToolset) can discover and call these tools
over the Model Context Protocol instead of them being hardcoded prompt text.

Run standalone (stdio transport, the standard for local MCP servers):
    python -m mcp_server.server

Run with the MCP Inspector for interactive testing:
    npx @modelcontextprotocol/inspector python -m mcp_server.server

To use this from an ADK agent, wrap it with ADK's MCPToolset pointed at
this script via a StdioServerParameters connection -- see README.md.
"""

from mcp.server.fastmcp import FastMCP

from mcp_server.wellness_tools import (
    breathing_exercise,
    journal_prompt,
    grounding_activity,
)

mcp = FastMCP("mindguard-wellness-tools")


@mcp.tool()
def get_breathing_exercise() -> str:
    """Return a short guided breathing exercise (box breathing) for
    acute stress relief. Use when the user reports high stress or
    anxiety in their check-in."""
    return breathing_exercise()


@mcp.tool()
def get_journal_prompt() -> str:
    """Return a 5-minute journaling prompt to help the user process
    what's affecting their mood. Use for low mood or rumination."""
    return journal_prompt()


@mcp.tool()
def get_grounding_activity() -> str:
    """Return a 5-4-3-2-1 sensory grounding exercise. Use when the
    user reports anxiety, overwhelm, or difficulty focusing."""
    return grounding_activity()


if __name__ == "__main__":
    # stdio transport -- the default for local/CLI MCP servers, and what
    # ADK's MCPToolset + StdioServerParameters expects to connect to.
    mcp.run(transport="stdio")