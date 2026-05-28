"""Tests for the standalone specter-mcp server.

The server exposes `fetch_company` as an MCP tool, but the bare async function
must remain importable and callable as a regular Python coroutine so the
provider boundary stays language-agnostic and tests don't have to go through
the MCP transport.
"""
import pytest

from mcp_servers.specter_mcp.server import fetch_company


@pytest.mark.asyncio
async def test_specter_mcp_fetch_company():
    result = await fetch_company("anduril.com")
    assert result is not None
    assert result["organization_name"] == "Anduril Industries"


@pytest.mark.asyncio
async def test_specter_mcp_returns_none_on_miss():
    result = await fetch_company("notreal.com")
    assert result is None
