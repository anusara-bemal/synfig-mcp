# Client Setup Guide (Claude Desktop, Cursor, VS Code, Claude Code)

This guide provides drop-in configuration snippets for configuring `synfig-mcp` with popular MCP client applications.

---

## 1. Claude Desktop

Edit your Claude Desktop configuration file:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Option A: Using `uvx` (Recommended)

```json
{
  "mcpServers": {
    "synfig": {
      "command": "uvx",
      "args": ["synfig-mcp"],
      "env": {
        "SYNFIG_MCP_WORKSPACE": "/path/to/your/synfig/projects",
        "SYNFIG_BIN": "/usr/bin/synfig"
      }
    }
  }
}
```

*On Windows, replace paths with Windows-style paths, e.g. `C:\\Users\\Username\\Documents\\SynfigProjects` and `C:\\Program Files\\Synfig\\bin\\synfig.exe`.*

### Option B: Using Python Virtualenv / Pip

```json
{
  "mcpServers": {
    "synfig": {
      "command": "python",
      "args": ["-m", "synfig_mcp"],
      "env": {
        "SYNFIG_MCP_WORKSPACE": "C:\\Users\\Username\\Documents\\SynfigProjects"
      }
    }
  }
}
```

---

## 2. Claude Code CLI

Add the server via `claude mcp add`:

```bash
# Using uvx
claude mcp add synfig -- uvx synfig-mcp

# Or with environment variables
claude mcp add synfig -e SYNFIG_MCP_WORKSPACE=/path/to/workspace -- uvx synfig-mcp
```

---

## 3. Cursor

In Cursor, navigate to **Settings** > **Features** > **MCP Servers** > **Add New MCP Server**:
- **Name**: `synfig`
- **Type**: `command`
- **Command**: `uvx synfig-mcp`

Or in `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "synfig": {
      "command": "uvx",
      "args": ["synfig-mcp"],
      "env": {
        "SYNFIG_MCP_WORKSPACE": "${workspaceFolder}"
      }
    }
  }
}
```

---

## 4. VS Code (Cline / Roo Code / Continue)

In your extension's MCP configuration settings (`cline_mcp_settings.json`):

```json
{
  "mcpServers": {
    "synfig": {
      "command": "python",
      "args": ["-m", "synfig_mcp"],
      "env": {
        "SYNFIG_MCP_WORKSPACE": "${workspaceFolder}",
        "SYNFIG_MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

---

## Verification

After configuring, run the `synfig_doctor` tool in your agent chat:
> *"Please run synfig_doctor to verify the Synfig MCP server connection."*

The tool will return detected paths, version information, and available render targets.
