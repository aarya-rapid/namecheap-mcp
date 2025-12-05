from __future__ import annotations

from .controllers.mcp_tools import mcp
from .config import server_settings


def main() -> None:
    """
    Entry point for the Namecheap MCP server.
    Exposes a streamable HTTP MCP endpoint.
    """
    mcp.settings.host = server_settings.host
    mcp.settings.port = server_settings.port
    mcp.run(transport="streamable-http")

    # mcp.run(
    #     transport="streamable-http",
    #     host=server_settings.host,
    #     port=server_settings.port,
    # )


if __name__ == "__main__":
    main()
