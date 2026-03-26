"""Run pytest for a block from the repository root.

This module executes pytest on a block's test directory in a subprocess, capturing output
and parsing results. It ensures the repository root is on PYTHONPATH so tests can import
blocks using the blocks.BlockName.src.module_name pattern.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

from faasr_blocks.builder.block_context import BlockContext
from faasr_blocks.builder.debug_log import debug_print
from faasr_blocks.builder.models import TestResult


class TestRunner:
    """
    Execute pytest on a block's test directory and capture results.

    Runs pytest as a subprocess from the repository root with PYTHONPATH configured
    to allow block imports (e.g., blocks.GetWeatherData.src.get_weather_data).
    """

    def __init__(self, context: BlockContext) -> None:
        self._context = context

    def run_tests(self) -> TestResult:
        """
        Run pytest on the block's tests/ directory and return structured results.

        Returns:
            TestResult with pass/fail status, exit code, captured output, and summary line.
        """
        block_path = self._context.block_path
        repo_root = self._context.repo_root
        tests_dir = block_path / "tests"
        if not tests_dir.is_dir():
            return TestResult(
                passed=False,
                exit_code=2,
                stderr="",
                stdout="",
                summary_line=f"tests directory missing: {tests_dir}",
            )

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(tests_dir),
            "-v",
            "--tb=short",
        ]
        env = dict(**os.environ)
        # Ensure repo root imports (e.g. blocks.*) resolve like local pytest.ini pythonpath
        existing = env.get("PYTHONPATH", "")
        sep = os.pathsep
        env["PYTHONPATH"] = f"{repo_root}{sep}{existing}" if existing else str(repo_root)

        debug_print("pytest cwd=", repo_root, "cmd=", " ".join(cmd))

        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            env=env,
            timeout=600,
        )
        out = proc.stdout or ""
        err = proc.stderr or ""
        combined = out + "\n" + err
        summary_line = _extract_summary(combined)
        passed = proc.returncode == 0
        return TestResult(
            passed=passed,
            exit_code=proc.returncode,
            stdout=out,
            stderr=err,
            summary_line=summary_line or f"exit_code={proc.returncode}",
        )


def _extract_summary(text: str) -> str:
    """
    Extract pytest's summary line from combined stdout/stderr.

    Looks for lines containing pytest result keywords (passed, failed, error, warnings)
    in the last ~8 lines of output.

    Args:
        text: Combined pytest stdout and stderr.

    Returns:
        Summary line (e.g., "5 passed in 0.12s") or empty string if not found.
    """
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    for ln in reversed(lines[-8:]):
        if re.search(r"\b(passed|failed|error|warnings?)\b", ln, re.I):
            return ln
    return ""
