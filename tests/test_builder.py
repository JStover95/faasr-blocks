"""Unit tests for Phase 2 block builder components."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from faasr_blocks.builder.artifact_parse import parse_marked_files
from faasr_blocks.builder.block_builder import _pytest_remediation_hints
from faasr_blocks.builder.block_context import BlockContext
from faasr_blocks.builder.llm import StaticMockLLM
from faasr_blocks.builder.static_validator import StaticValidator
from faasr_blocks.builder.test_runner import TestRunner
from faasr_blocks.builder.test_validator import ContractTestCoverageValidator
from faasr_blocks.models.contract import Contract

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CONTRACT = REPO_ROOT / "blocks" / "GetWeatherData" / "contract.json"
SCHEMA_PATH = REPO_ROOT / "schema" / "contract_schema.json"


def _minimal_runner_contract() -> Contract:
    """Valid contract for components that only need repo_root/block_path (e.g. TestRunner)."""
    return Contract.model_validate(
        {
            "block_name": "Minimal",
            "version": "1.0.0",
            "function": {"name": "x", "arguments": {}, "return_type": "None"},
            "s3_outputs": [],
            "required_secrets": [],
            "preconditions": "",
            "postconditions": "",
            "methodology": "",
            "conditional_return": None,
            "metadata": {
                "role": "r",
                "data_type": "d",
                "methodology_category": "m",
                "tags": [],
            },
            "dependencies": {"python_packages": []},
        }
    )


@pytest.fixture
def sample_contract() -> Contract:
    return Contract.from_json_path(SAMPLE_CONTRACT)


def test_parse_marked_files_roundtrip():
    text = textwrap.dedent(
        """
        ### FILE: tests/test_foo.py
        ```python
        x = 1
        ```

        ### FILE: tests/fixtures/a.json
        ```json
        {"a": 1}
        ```
        """
    )
    files = parse_marked_files(text)
    assert "tests/test_foo.py" in files
    assert files["tests/test_foo.py"].strip() == "x = 1"
    assert '"a": 1' in files["tests/fixtures/a.json"]


def test_pytest_remediation_hints_magicmock_write():
    out = _pytest_remediation_hints(
        "E   TypeError: write() argument must be str, not MagicMock\n",
    )
    assert "response.json()" in out
    assert "json.dump" in out


def test_static_validator_accepts_get_weather_source(sample_contract: Contract):
    block_path = REPO_ROOT / "blocks" / "GetWeatherData"
    ctx = BlockContext(
        contract=sample_contract,
        block_path=block_path,
        repo_root=REPO_ROOT,
        schema_path=SCHEMA_PATH,
    )
    r = StaticValidator(ctx).validate()
    assert r.ok, r.errors


def test_static_validator_wrong_param_order(tmp_path: Path):
    c = Contract.model_validate(
        {
            "block_name": "Tmp",
            "version": "1.0.0",
            "function": {
                "name": "f",
                "arguments": {
                    "a": {"type": "str", "description": ""},
                    "b": {"type": "str", "description": ""},
                },
                "return_type": "None",
            },
            "s3_outputs": [],
            "required_secrets": [],
            "preconditions": "",
            "postconditions": "",
            "methodology": "",
            "conditional_return": None,
            "metadata": {
                "role": "r",
                "data_type": "d",
                "methodology_category": "m",
                "tags": [],
            },
            "dependencies": {"python_packages": []},
        }
    )
    block_path = tmp_path / "blocks" / "Tmp"
    src_dir = block_path / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "f.py").write_text(
        "def f(b, a):\n    pass\n",
        encoding="utf-8",
    )
    ctx = BlockContext(
        contract=c,
        block_path=block_path,
        repo_root=tmp_path,
        schema_path=SCHEMA_PATH,
    )
    r = StaticValidator(ctx).validate()
    assert not r.ok
    assert any("Parameter list mismatch" in e for e in r.errors)


def test_static_validator_missing_secret(tmp_path: Path):
    c = Contract.model_validate(
        {
            "block_name": "Tmp",
            "version": "1.0.0",
            "function": {
                "name": "f",
                "arguments": {},
                "return_type": "None",
            },
            "s3_outputs": [{"filename": "out.txt", "format": "text", "description": ""}],
            "required_secrets": ["MY_KEY"],
            "preconditions": "",
            "postconditions": "",
            "methodology": "",
            "conditional_return": None,
            "metadata": {
                "role": "r",
                "data_type": "d",
                "methodology_category": "m",
                "tags": [],
            },
            "dependencies": {"python_packages": []},
        }
    )
    block_path = tmp_path / "blocks" / "Tmp"
    src_dir = block_path / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "f.py").write_text(
        textwrap.dedent(
            """
            from FaaSr_py.client.py_client_stubs import faasr_put_file

            def f():
                faasr_put_file(local_file="x", remote_file="out.txt", remote_folder=".")
            """
        ),
        encoding="utf-8",
    )
    ctx = BlockContext(
        contract=c,
        block_path=block_path,
        repo_root=tmp_path,
        schema_path=SCHEMA_PATH,
    )
    r = StaticValidator(ctx).validate()
    assert not r.ok
    assert any("MY_KEY" in e for e in r.errors)


def test_test_runner_passes_minimal_block(tmp_path: Path):
    """Create a tiny synthetic repo layout under tmp_path."""
    repo = tmp_path / "repo"
    blk = repo / "blocks" / "Minimal"
    (blk / "tests").mkdir(parents=True)
    (blk / "tests" / "test_x.py").write_text(
        "def test_ok():\n    assert 1 == 1\n",
        encoding="utf-8",
    )
    ctx = BlockContext(
        contract=_minimal_runner_contract(),
        block_path=blk,
        repo_root=repo,
        schema_path=SCHEMA_PATH,
    )
    tr = TestRunner(ctx)
    res = tr.run_tests()
    assert res.passed, res.stdout + res.stderr


def test_test_runner_fails_on_assert(tmp_path: Path):
    repo = tmp_path / "repo"
    blk = repo / "blocks" / "Bad"
    (blk / "tests").mkdir(parents=True)
    (blk / "tests" / "test_x.py").write_text(
        "def test_fail():\n    assert 1 == 2\n",
        encoding="utf-8",
    )
    ctx = BlockContext(
        contract=_minimal_runner_contract(),
        block_path=blk,
        repo_root=repo,
        schema_path=SCHEMA_PATH,
    )
    tr = TestRunner(ctx)
    res = tr.run_tests()
    assert not res.passed


def test_test_contract_validator_json_ok(tmp_path: Path, sample_contract: Contract):
    block_path = tmp_path / "blocks" / "GetWeatherData"
    tests_dir = block_path / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_get_weather_data.py").write_text(
        "def test_x():\n    assert True\n",
        encoding="utf-8",
    )
    llm = StaticMockLLM([r'{"ok": true}'])
    ctx = BlockContext(
        contract=sample_contract,
        block_path=block_path,
        repo_root=tmp_path,
        schema_path=SCHEMA_PATH,
    )
    v = ContractTestCoverageValidator(llm, ctx)
    r = v.validate()
    assert r.ok


def test_test_contract_validator_json_gaps(tmp_path: Path, sample_contract: Contract):
    block_path = tmp_path / "blocks" / "GetWeatherData"
    tests_dir = block_path / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_get_weather_data.py").write_text(
        "def test_x():\n    assert True\n",
        encoding="utf-8",
    )
    llm = StaticMockLLM(
        [r'{"ok": false, "gaps": ["missing faasr_put_file assertions", "no secret tests"]}']
    )
    ctx = BlockContext(
        contract=sample_contract,
        block_path=block_path,
        repo_root=tmp_path,
        schema_path=SCHEMA_PATH,
    )
    v = ContractTestCoverageValidator(llm, ctx)
    r = v.validate()
    assert not r.ok
    assert len(r.errors) >= 1
