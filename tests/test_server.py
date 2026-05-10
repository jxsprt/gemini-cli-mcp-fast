"""Tests for gemini-mcp-server."""

import os
import subprocess
from unittest.mock import ANY, MagicMock, patch

import pytest

# Point to the source tree so we test the installed package
from gemini_mcp_server import gemini_prompt, gemini_plan, gemini_version


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_env():
    """Ensure env vars don't leak between tests."""
    keys = ["GEMINI_CLI_PATH", "GEMINI_TIMEOUT", "GEMINI_PLAN_TIMEOUT", "GEMINI_MAX_PROMPT"]
    saved = {k: os.environ.pop(k, None) for k in keys}
    yield
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run to return a successful result."""
    with patch.object(subprocess, "run") as mock:
        mock.return_value = MagicMock(
            returncode=0,
            stdout="mock output\n",
            stderr="",
        )
        yield mock


@pytest.fixture
def mock_subprocess_fail():
    """Mock subprocess.run to return a failure."""
    with patch.object(subprocess, "run") as mock:
        mock.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="something went wrong",
        )
        yield mock


@pytest.fixture
def mock_subprocess_timeout():
    """Mock subprocess.run to raise TimeoutExpired."""
    with patch.object(subprocess, "run") as mock:
        mock.side_effect = subprocess.TimeoutExpired(cmd="gemini", timeout=10)
        yield mock


@pytest.fixture
def mock_bin():
    """Ensure shutil.which finds a fake gemini binary."""
    with patch("server.shutil.which", return_value="/usr/local/bin/gemini"):
        yield


# ── gemini_version ──────────────────────────────────────────────────────────


class TestGeminiVersion:
    def test_returns_version(self, mock_subprocess, mock_bin):
        mock_subprocess.return_value = MagicMock(
            returncode=0, stdout="0.41.2\n", stderr=""
        )
        result = gemini_version()
        assert result == "0.41.2"

    def test_timeout(self, mock_subprocess_timeout, mock_bin):
        result = gemini_version()
        assert "Error" in result
        assert "timed out" in result

    def test_binary_not_found(self):
        with patch("server.shutil.which", return_value=None):
            result = gemini_version()
            assert "Error" in result
            assert "not found" in result


# ── gemini_prompt ────────────────────────────────────────────────────────────


class TestGeminiPrompt:
    def test_basic_prompt(self, mock_subprocess, mock_bin):
        result = gemini_prompt("Say hello")
        assert result == "mock output"
        # Verify it used auto_edit (safe default)
        args = mock_subprocess.call_args[0][0]
        assert "--approval-mode" in args
        assert "auto_edit" in args

    def test_with_model(self, mock_subprocess, mock_bin):
        gemini_prompt("Hi", model="gemini-2.5-pro")
        args = mock_subprocess.call_args[0][0]
        assert "-m" in args
        assert "gemini-2.5-pro" in args

    def test_with_output_format(self, mock_subprocess, mock_bin):
        gemini_prompt("Hi", output_format="json")
        args = mock_subprocess.call_args[0][0]
        assert "-o" in args
        assert "json" in args

    def test_dangerous_mode(self, mock_subprocess, mock_bin):
        gemini_prompt("Hi", dangerous=True)
        args = mock_subprocess.call_args[0][0]
        assert "yolo" in args  # dangerous=True → yolo

    def test_safe_default(self, mock_subprocess, mock_bin):
        gemini_prompt("Hi")
        args = mock_subprocess.call_args[0][0]
        assert "yolo" not in args  # not dangerous by default

    def test_prompt_truncation(self, mock_subprocess, mock_bin):
        long_prompt = "x" * 200_000
        result = gemini_prompt(long_prompt)
        assert result == "mock output"  # didn't crash
        args = mock_subprocess.call_args[0][0]
        prompt_arg = args[args.index("-p") + 1]
        assert len(prompt_arg) <= 100_000  # was truncated

    def test_timeout(self, mock_subprocess_timeout, mock_bin):
        result = gemini_prompt("Hi")
        assert "Error" in result
        assert "timed out" in result

    def test_subprocess_failure(self, mock_subprocess_fail, mock_bin):
        result = gemini_prompt("Hi")
        assert "Error" in result

    def test_empty_response(self, mock_subprocess, mock_bin):
        mock_subprocess.return_value = MagicMock(
            returncode=0, stdout="\n  \n", stderr=""
        )
        result = gemini_prompt("Hi")
        assert result == "(empty response)"


# ── gemini_plan ──────────────────────────────────────────────────────────────


class TestGeminiPlan:
    def test_basic_plan(self, mock_subprocess, mock_bin):
        result = gemini_plan("Review this code")
        assert result == "mock output"
        # Verify it used plan mode
        args = mock_subprocess.call_args[0][0]
        assert "--approval-mode" in args
        assert "plan" in args

    def test_with_model(self, mock_subprocess, mock_bin):
        gemini_plan("Review", model="gemini-2.5-pro")
        args = mock_subprocess.call_args[0][0]
        assert "-m" in args
        assert "gemini-2.5-pro" in args

    def test_include_directories(self, mock_subprocess, mock_bin):
        with patch("server.os.getcwd", return_value="/home/user/project"):
            gemini_plan("Review", include_directories="src,tests")
            args = mock_subprocess.call_args[0][0]
            assert "--include-directories" in args
            idx = args.index("--include-directories")
            dirs = args[idx + 1]
            assert "src" in dirs
            assert "tests" in dirs

    def test_out_of_workspace_path_rejected(self, mock_subprocess, mock_bin):
        with patch("server.os.getcwd", return_value="/home/user/project"):
            with patch("server.logger.warning") as mock_log:
                gemini_plan("Review", include_directories="/etc")
                args = mock_subprocess.call_args[0][0]
                # /etc should NOT appear in the args
                if "--include-directories" in args:
                    idx = args.index("--include-directories")
                    dirs = args[idx + 1]
                    assert "/etc" not in dirs
                mock_log.assert_called_once_with(
                    "Ignored out-of-workspace path: %s", "/etc"
                )

    def test_timeout(self, mock_subprocess_timeout, mock_bin):
        result = gemini_plan("Review")
        assert "Error" in result
        assert "timed out" in result
