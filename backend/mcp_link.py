"""One MCP client connection, shared by the FastAPI routes.

The API does not read or write shop data itself. When a route needs a fact or
needs to move money, it calls a tool on the same MCP server the agents use, so
there is still exactly one layer between the shop database and everything else.

The connection is opened once when the API starts and closed when it stops,
rather than spawning a server process per request.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from .config import MCP_INIT_TIMEOUT_SECONDS, MCP_READ_TIMEOUT_SECONDS, PROJECT_ROOT

SERVER_SCRIPT = PROJECT_ROOT / "mcp_server" / "server.py"
WORKING_DB_RELATIVE = "data/campus_customs_new.db"


class MCPLink:
    """Holds the shared client and unwraps tool results into plain dicts."""

    def __init__(self) -> None:
        self._client: Client | None = None

    async def open(self) -> None:
        transport = StdioTransport(
            command=sys.executable,
            args=[str(SERVER_SCRIPT)],
            env={"CAMPUS_CUSTOMS_DB": WORKING_DB_RELATIVE},
        )
        # Same generous handshake window as the agents use; see config.py.
        self._client = Client(
            transport,
            init_timeout=MCP_INIT_TIMEOUT_SECONDS,
            timeout=MCP_READ_TIMEOUT_SECONDS,
        )
        await self._client.__aenter__()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None

    async def call(self, tool: str, **arguments: Any) -> dict[str, Any]:
        """Call one MCP tool and return its payload as a dict."""
        if self._client is None:
            raise RuntimeError("MCP link is not open.")
        result = await self._client.call_tool(tool, arguments)

        # FastMCP returns structured content when the tool declares a shape,
        # and text content otherwise. Prefer the structured form.
        data = getattr(result, "structured_content", None)
        if isinstance(data, dict) and "result" in data and len(data) == 1:
            data = data["result"]
        if isinstance(data, dict):
            return data

        content = getattr(result, "content", None)
        if content:
            text = getattr(content[0], "text", None)
            if text:
                return json.loads(text)
        return {}


link = MCPLink()
