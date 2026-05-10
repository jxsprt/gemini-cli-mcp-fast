# gemini-cli-mcp-fast

**FastMCP server wrapping Google's Gemini CLI** — use Gemini models from any MCP client.

- **PyPI:** `pip install gemini-cli-mcp-fast`
- **License:** MIT
- **Requires:** Python ≥3.11, Node.js, Gemini CLI

## Prerequisites

```bash
npm install -g @google/gemini-cli
gemini --version          # Verify install
gemini                    # Run once to complete OAuth login
```

## Installation

```bash
pip install gemini-cli-mcp-fast
```

Run as a module:
```bash
python -m gemini_mcp_server
```

## Configuration — Hermes Agent

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  gemini-cli:
    command: "python3"
    args: ["-m", "gemini_mcp_server"]
    timeout: 240
```

Tools become available as `mcp_gemini_cli_*`.

## Configuration — Claude Desktop

```json
{
  "mcpServers": {
    "gemini-cli": {
      "command": "python3",
      "args": ["-m", "gemini_mcp_server"]
    }
  }
}
```

## Tools

### `gemini_prompt`
Send any prompt to Gemini CLI non-interactively. Safe by default — uses `--approval-mode auto-edit`. Pass `dangerous=true` for full yolo mode.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ✅ | — | Max ~100K chars |
| `model` | string | ❌ | CLI default | e.g. `gemini-2.5-flash` |
| `output_format` | string | ❌ | `text` | `text`, `json`, or `stream-json` |
| `dangerous` | bool | ❌ | `false` | Use `--approval-mode yolo` |

### `gemini_plan`
Read-only audit and review mode. Uses `--approval-mode plan` — guarantees no file mutations or shell execution.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ✅ | — | Analysis/review request |
| `model` | string | ❌ | CLI default | Gemini model |
| `include_directories` | string | ❌ | — | Comma-separated additional dirs |

### `gemini_version`
Returns the installed Gemini CLI version.

## Verification

```bash
python -c "
import gemini_mcp_server as s
print('Version:', s.gemini_version())
print('Prompt:', s.gemini_prompt('Say hello in one word'))
print('Plan:', s.gemini_plan('What tools does this server have?'))
"
```

## License

MIT
