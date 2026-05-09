"""
gemini-mcp-server — FastMCP server wrapping Google's Gemini CLI.

Exposes Gemini CLI as MCP tools consumable by any MCP client
(Hermes Agent, Claude Code, Claude Desktop, Cursor, etc.).

Powered by FastMCP (https://gofastmcp.com).

Tools:
  - gemini_prompt    → Send a prompt to Gemini CLI (non-interactive, full power)
  - gemini_plan      → Read-only audit/review mode (--approval-mode plan)
  - gemini_version   → Get Gemini CLI version
"""

import shutil
import subprocess
from typing import Optional

from fastmcp import FastMCP

# ── Server ────────────────────────────────────────────────────────────────

mcp = FastMCP("Gemini CLI MCP Server")

# ── Constants ──────────────────────────────────────────────────────────────

GEMINI_BIN = shutil.which("gemini")
if GEMINI_BIN is None:
    raise RuntimeError(
        "Gemini CLI not found on PATH. Install it with: npm install -g @google/gemini-cli"
    )

DEFAULT_TIMEOUT = 120   # Gemini CLI retries capacity errors up to 7 times
PLAN_TIMEOUT = 240      # longer for read-only audits with 1M token context
MAX_PROMPT_LENGTH = 100_000


# ── Helper ─────────────────────────────────────────────────────────────────

def _run_gemini(args: list[str], timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run `gemini <args>` and return structured result.

    Returns dict with keys: success, output, error.
    """
    cmd = [GEMINI_BIN] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            return {
                "success": False,
                "output": stdout,
                "error": stderr or f"Exit code {result.returncode}",
            }

        return {"success": True, "output": stdout, "error": None}

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"Command timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "output": "",
            "error": f"Gemini CLI not found at {GEMINI_BIN}. Install: npm install -g @google/gemini-cli",
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
        }


# ── Tools ──────────────────────────────────────────────────────────────────


@mcp.tool(
    name="gemini_prompt",
    description=(
        "Send a prompt to Gemini CLI in non-interactive mode. "
        "The full power of Gemini models — coding, research, Q&A, analysis. "
        "Supports optional model selection and output format."
    ),
)
def gemini_prompt(
    prompt: str,
    model: Optional[str] = None,
    output_format: Optional[str] = None,
) -> str:
    """Execute a prompt via Gemini CLI.

    Args:
        prompt: The prompt text to send (max ~100K chars).
        model: Gemini model to use (e.g., gemini-3-flash-preview, gemini-2.5-pro).
               Defaults to gemini CLI's built-in default.
        output_format: 'text' (default), 'json', or 'stream-json'.
                       JSON includes token/cost stats in the envelope.

    Returns:
        Gemini CLI output as a string.
    """
    if len(prompt) > MAX_PROMPT_LENGTH:
        prompt = prompt[:MAX_PROMPT_LENGTH]

    args = ["-p", prompt, "--approval-mode", "yolo"]

    if model:
        args += ["-m", model]
    if output_format:
        args += ["-o", output_format]

    result = _run_gemini(args, timeout=DEFAULT_TIMEOUT)

    if result["success"]:
        return result["output"] or "(empty response)"
    else:
        error_msg = result["error"] or "unknown error"
        return f"Error: {error_msg}"


@mcp.tool(
    name="gemini_plan",
    description=(
        "Read-only audit, code review, and research via Gemini CLI. "
        "Uses --approval-mode plan which guarantees NO file mutations or shell execution. "
        "Safe for whole-repo analysis, code reviews, vulnerability assessments, "
        "architecture audits, and deep research."
    ),
)
def gemini_plan(
    prompt: str,
    model: Optional[str] = None,
    include_directories: Optional[str] = None,
) -> str:
    """Run Gemini CLI in read-only plan mode — no mutations possible.

    Args:
        prompt: Analysis question or review request.
        model: Gemini model (optional, defaults to gemini CLI default).
        include_directories: Comma-separated additional dirs to include in workspace.

    Returns:
        Gemini CLI's analysis/plan output.
    """
    if len(prompt) > MAX_PROMPT_LENGTH:
        prompt = prompt[:MAX_PROMPT_LENGTH]

    args = ["-p", prompt, "--approval-mode", "plan"]

    if model:
        args += ["-m", model]
    if include_directories:
        args += ["--include-directories", include_directories]

    result = _run_gemini(args, timeout=PLAN_TIMEOUT)

    if result["success"]:
        return result["output"] or "(empty response)"
    else:
        error_msg = result["error"] or "unknown error"
        return f"Error: {error_msg}"


@mcp.tool(
    name="gemini_version",
    description="Get the installed Gemini CLI version.",
)
def gemini_version() -> str:
    """Get Gemini CLI version info."""
    try:
        result = subprocess.run(
            [GEMINI_BIN, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = (result.stdout or result.stderr or "").strip()
        return output or "(no version info)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 10s"
    except FileNotFoundError:
        return f"Error: Gemini CLI not found at {GEMINI_BIN}"
    except Exception as e:
        return f"Error: {e}"


# ── Entrypoint ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
