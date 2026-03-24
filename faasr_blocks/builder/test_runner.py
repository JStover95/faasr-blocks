"""Run pytest for a block from the repository root."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from faasr_blocks.builder.debug_log import debug_print
from faasr_blocks.builder.models import TestResult


class TestRunner:
    """Execute pytest on ``block_path / \"tests\"`` with repo root on PYTHONPATH."""

    def run_tests(self, block_path: Path, repo_root: Path) -> TestResult:
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
    # pytest ends with e.g. "5 passed in 0.12s" or "1 failed, 2 passed"
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    for ln in reversed(lines[-8:]):
        if re.search(r"\b(passed|failed|error|warnings?)\b", ln, re.I):
            return ln
    return ""
