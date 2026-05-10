"""gemini-mcp-server — FastMCP server wrapping Google's Gemini CLI."""

from .server import mcp, gemini_prompt, gemini_plan, gemini_version, main

__all__ = ["mcp", "gemini_prompt", "gemini_plan", "gemini_version", "main"]
