# specter-mcp

Standalone Model Context Protocol server exposing Specter company enrichment as a tool.

POC: reads fixtures from `../../fixtures/<domain>/specter.json`.
Production: would proxy to the real Specter REST API behind the same tool contract.

## Run

```bash
python -m mcp_servers.specter_mcp.server
```

## Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python -m mcp_servers.specter_mcp.server
```

Then call `fetch_company` with `{"domain": "anduril.com"}`.

## Connect to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "specter": {
      "command": "python",
      "args": ["-m", "mcp_servers.specter_mcp.server"],
      "cwd": "/path/to/pre-meeting-brief"
    }
  }
}
```
