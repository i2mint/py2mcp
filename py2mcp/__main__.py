"""``python -m py2mcp`` — serve an MCP server over stdio from refs/config.

See :mod:`py2mcp.serve`. This is the command a packaged integration (e.g. a
Claude Desktop ``.mcpb`` bundle) launches to run the server.
"""

from py2mcp.serve import main

if __name__ == "__main__":
    main()
