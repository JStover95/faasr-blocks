"""Tests for orchestrator markdown summary."""

from __future__ import annotations

from pathlib import Path

import pytest

from faasr_blocks.builder.models import BuildResult
from faasr_blocks.models.contract import Contract
from faasr_blocks.orchestrator.summary import format_workflow_summary


@pytest.fixture
def sample_contract() -> Contract:
    path = Path(__file__).resolve().parent.parent / "blocks" / "GetWeatherData" / "contract.json"
    return Contract.from_json_path(path)


def test_format_workflow_summary_includes_request_and_blocks(sample_contract: Contract) -> None:
    from faasr_blocks.builder.models import TestResult as PytestTestResult

    br = BuildResult(
        success=True,
        block_path="/tmp/blocks/Foo",
        message="ok",
        attempts=1,
        test_result=PytestTestResult(passed=True, exit_code=0, summary_line="1 passed"),
    )
    md = format_workflow_summary(
        user_request="Do something useful",
        reused_blocks=[(sample_contract, "Matches OpenWeather fetch.")],
        new_blocks=[(sample_contract, br)],
        workflow_dag=[("A", "B")],
    )
    assert "Do something useful" in md
    assert "GetWeatherData" in md
    assert "reused" in md
    assert "new" in md
    assert "A → B" in md or "A" in md
