from __future__ import annotations

from .services.mcp_provider import mcp


def main() -> None:
    """
    Stdio entrypoint for Smithery.
    This runs the same MCP tools, but over stdio instead of HTTP.
    """
    # No host/port here – Smithery talks to us via stdio.
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
