"""Arcane MCP server — entrypoint that registers all tools."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from opencode_arcane_mcp.tools import (
    containers,
    environments,
    images,
    networks,
    projects,
    system,
    volumes,
    webhooks,
)

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

mcp = FastMCP("opencode-arcane-mcp")

# Register all tool sets with the MCP server
containers.register(mcp)
environments.register(mcp)
images.register(mcp)
networks.register(mcp)
system.register(mcp)
volumes.register(mcp)
projects.register(mcp)
webhooks.register(mcp)

logger.info("Registered 8 tool modules")


def main() -> None:
    """Run the MCP server over stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
