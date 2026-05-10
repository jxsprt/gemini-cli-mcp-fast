# Gemini CLI MCP Server

A lightweight [FastMCP](https://gofastmcp.com) server that wraps Google's [Gemini CLI](https://github.com/google-gemini/gemini-cli) as MCP tools. Works with any MCP client — Hermes Agent, Claude Code, Claude Desktop, Cursor, etc.

## Prerequisites

- **Node.js** — for the Gemini CLI
- **Python 3.11+** — for the MCP server
- **Gemini CLI** — installed and authenticated

```bash
npm install -g @google/gemini-cli
gemini --version          # Verify install
gemini                    # Run once to complete OAuth login
```

## Installation

```bash
# Clone the repo
git clone https://github.com/jxsprt/gemini-mcp-server.git
cd gemini-mcp-server

# Create venv and install deps
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Configuration

Add to your MCP client's config:

### Hermes Agent (`~/.hermes/config.yaml`)

```yaml
mcp_servers:
  gemini-cli:
    command: "/path/to/gemini-mcp-server/.venv/bin/python3"
    args: ["/path/to/gemini-mcp-server/server.py"]
    timeout: 240
```

Restart your Hermes gateway. Tools will be available as `mcp_gemini_cli_*`.

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "gemini-cli": {
      "command": "/path/to/gemini-mcp-server/.venv/bin/python3",
      "args": ["/path/to/gemini-mcp-server/server.py"]
    }
  }
}
```

### Claude Code

```bash
fastmcp install claude-code /path/to/gemini-mcp-server/server.py
```

### Cursor

```bash
fastmcp install cursor /path/to/gemini-mcp-server/server.py -e .
```

## Tools

### `gemini_prompt`

Send any prompt to Gemini CLI non-interactively. Supports model selection and JSON output.

**Safe by default** — uses `--approval-mode auto-edit` (auto-approves file edits, prompts for shell). Pass `dangerous=true` for full `yolo` mode.

```python
gemini_prompt(prompt="Explain TCP handshake", model="gemini-2.5-flash")
gemini_prompt(prompt="Refactor this module", dangerous=True)     # full auto-approval
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ✅ | — | Prompt text (max ~100K chars) |
| `model` | string | ❌ | CLI default | Model name (e.g., `gemini-3-flash-preview`) |
| `output_format` | string | ❌ | `text` | `text`, `json`, or `stream-json` |
| `dangerous` | bool | ❌ | `false` | Use `--approval-mode yolo` (auto-approves shell) |

### `gemini_plan`

Read-only audit and review mode. Uses `--approval-mode plan` — **guarantees no file mutations or shell execution**. Safe for whole-repo analysis and code reviews.

```python
gemini_plan(prompt="Review this auth module for security issues")
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ✅ | — | Analysis question or review request |
| `model` | string | ❌ | CLI default | Gemini model |
| `include_directories` | string | ❌ | — | Comma-separated additional dirs |

### `gemini_version`

Returns the installed Gemini CLI version.

```python
gemini_version()  # → "0.41.2"
```

## Verification

```bash
cd /path/to/gemini-mcp-server
.venv/bin/python -c "
import server
print('Version:', server.gemini_version())
print('Prompt:', server.gemini_prompt('Say hello in one word'))
print('Plan:', server.gemini_plan('What tools does this server have?'))
"
```

## How It Works

The server shells out to `gemini -p "prompt" --approval-mode yolo` for each tool call. It does NOT use the Google Gen AI Python SDK — it goes through the Gemini CLI binary (OAuth-authenticated).

**Key design decisions:**
- **Stdio transport** — runs as a subprocess of your MCP client
- **No hardcoded paths** — discovers `gemini` on PATH
- **No API keys in config** — uses the CLI's existing OAuth session
- **Retry-friendly** — generous timeouts (120s default, 240s for plan mode) to handle Gemini's capacity retries

## Notes

- **Capacity errors**: Gemini's reasoning models can hit rate limits. The CLI retries up to 7 times with backoff. If it fails, try again later or use a different model.
- **Plan mode is safe**: `--approval-mode plan` explicitly prevents the agent from writing files or executing shell commands. Read-only, guaranteed.
- **1M token context**: Gemini CLI supports the full 1M token context window of Gemini models.

## License

MIT
