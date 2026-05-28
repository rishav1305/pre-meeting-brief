"""Standalone Specter MCP server.

Exposes a single tool `fetch_company(domain)` returning the Specter enrichment
payload for a company. POC: reads from ../../fixtures/<domain>/specter.json.
Production: would call the real Specter REST API.

Run standalone:
    python -m mcp_servers.specter_mcp.server

Or via MCP Inspector for ad-hoc testing:
    npx @modelcontextprotocol/inspector python -m mcp_servers.specter_mcp.server
"""
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"

mcp = FastMCP("specter-mcp")


@mcp.tool()
async def fetch_company(domain: str) -> dict | None:
    """Fetch enrichment for a company by domain.

    Returns Specter v1 schema; see api.tryspecter.com docs.
    For this POC: reads from ../../fixtures/<domain>/specter.json.

    Returns None if domain not in Specter coverage.
    """
    path = FIXTURES_DIR / domain / "specter.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


if __name__ == "__main__":
    mcp.run()
