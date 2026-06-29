"""Arcane MCP server — entrypoint that registers all tools."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from arcane_mcp.tools import (
    activities,
    containers,
    environments,
    images,
    networks,
    operations,
    ports,
    projects,
    registries,
    system,
    updater,
    volumes,
    vulnerabilities,
    webhooks,
)

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

mcp = FastMCP("opencode-arcane-mcp")

# Register all tool sets with the MCP server
activities.register(mcp)
containers.register(mcp)
environments.register(mcp)
images.register(mcp)
networks.register(mcp)
operations.register(mcp)
ports.register(mcp)
projects.register(mcp)
registries.register(mcp)
system.register(mcp)
updater.register(mcp)
volumes.register(mcp)
vulnerabilities.register(mcp)
webhooks.register(mcp)

logger.info("Registered 14 tool modules")


def main() -> None:
    """Run the MCP server over stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
