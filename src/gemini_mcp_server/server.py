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

import logging
import os
import shutil
import subprocess
from typing import Optional

from fastmcp import FastMCP

# ── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=__import__("sys").stderr,
)
logger = logging.getLogger("gemini-mcp")

# ── Server ─────────────────────────────────────────────────────────────────

mcp = FastMCP("Gemini CLI MCP Server")

# ── Configuration (env vars with sensible defaults) ────────────────────────

_GEMINI_CLI_PATH = os.environ.get("GEMINI_CLI_PATH")
DEFAULT_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "120"))
PLAN_TIMEOUT = int(os.environ.get("GEMINI_PLAN_TIMEOUT", "240"))
MAX_PROMPT_LENGTH = int(os.environ.get("GEMINI_MAX_PROMPT", "100000"))
HTTP_ENABLED = os.environ.get("GEMINI_MCP_HTTP", "").lower() in ("1", "true", "yes")


def _get_gemini_bin() -> str:
    """Locate the gemini CLI binary. Returns full path or raises RuntimeError."""
    if _GEMINI_CLI_PATH:
        path = _GEMINI_CLI_PATH
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
        raise RuntimeError(
            f"GEMINI_CLI_PATH set to '{path}' but file not found or not executable. "
            "Fix the path or unset it to auto-discover."
        )
    path = shutil.which("gemini")
    if path is None:
        raise RuntimeError(
            "Gemini CLI not found on PATH. Install it with: npm install -g @google/gemini-cli, "
            "or set the GEMINI_CLI_PATH environment variable."
        )
    return path


# ── Helper ─────────────────────────────────────────────────────────────────


def _run_gemini(args: list[str], timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run `gemini <args>` and return structured result.

    Returns dict with keys: success, output, error.
    """
    gemini_bin = _get_gemini_bin()
    cmd = [gemini_bin] + args
    logger.info("Running: %s", " ".join(cmd))

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
            logger.warning("Non-zero exit %d: %s", result.returncode, stderr[:200])
            return {
                "success": False,
                "output": stdout,
                "error": stderr or f"Exit code {result.returncode}",
            }

        logger.info("Success (%d chars)", len(result.stdout))
        return {"success": True, "output": stdout, "error": None}

    except subprocess.TimeoutExpired:
        logger.warning("Timed out after %ds", timeout)
        return {
            "success": False,
            "output": "",
            "error": f"Command timed out after {timeout}s",
        }
    except FileNotFoundError:
        msg = f"Gemini CLI not found at {gemini_bin}"
        logger.error(msg)
        return {"success": False, "output": "", "error": msg}
    except Exception as e:
        logger.exception("Unexpected error")
        return {"success": False, "output": "", "error": str(e)}


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
    dangerous: bool = False,
) -> str:
    """Execute a prompt via Gemini CLI.

    By default uses --approval-mode auto-edit (safe for file edits in working dir).
    Pass dangerous=True to use --approval-mode yolo (auto-approves ALL actions
    including arbitrary shell commands).

    Args:
        prompt: The prompt text to send (max ~100K chars).
        model: Gemini model to use (e.g., gemini-3-flash-preview, gemini-2.5-pro).
               Defaults to gemini CLI's built-in default.
        output_format: 'text' (default), 'json', or 'stream-json'.
                       JSON includes token/cost stats in the envelope.
        dangerous: If True, uses --approval-mode yolo (auto-approves shell cmds).
                   Defaults to False (--approval-mode auto-edit).

    Returns:
        Gemini CLI output as a string.
    """
    if len(prompt) > MAX_PROMPT_LENGTH:
        prompt = prompt[:MAX_PROMPT_LENGTH]

    approval = "yolo" if dangerous else "auto_edit"
    args = ["-p", prompt, "--approval-mode", approval]

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
                             Only includes subdirectories of the current working directory
                             for safety.

    Returns:
        Gemini CLI's analysis/plan output.
    """
    if len(prompt) > MAX_PROMPT_LENGTH:
        prompt = prompt[:MAX_PROMPT_LENGTH]

    args = ["-p", prompt, "--approval-mode", "plan"]

    if model:
        args += ["-m", model]

    # Validate include_directories — restrict to CWD subdirectories
    if include_directories:
        cwd = os.getcwd()
        validated = []
        for d in include_directories.split(","):
            d = d.strip()
            abs_d = os.path.abspath(os.path.join(cwd, d)) if not os.path.isabs(d) else d
            if abs_d.startswith(cwd.rstrip("/") + "/") or abs_d == cwd:
                validated.append(d)
            else:
                logger.warning("Ignored out-of-workspace path: %s", d)
        if validated:
            args += ["--include-directories", ",".join(validated)]

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
        gemini_bin = _get_gemini_bin()
        result = subprocess.run(
            [gemini_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = (result.stdout or result.stderr or "").strip()
        return output or "(no version info)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 10s"
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error: {e}"


# ── Entrypoint ─────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for pip-installed package."""
    if HTTP_ENABLED:
        logger.info("Starting HTTP transport on port 8000")
        mcp.run(transport="http")
    else:
        logger.info("Starting stdio transport")
        mcp.run()


if __name__ == "__main__":
    main()
