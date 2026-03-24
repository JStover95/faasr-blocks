"""Tests for contract and block layout validators."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from faasr_blocks.models.contract import Contract
from faasr_blocks.validation.block_validator import BlockValidator
from faasr_blocks.validation.contract_validator import ContractValidator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "contract_schema.json"
SAMPLE_CONTRACT = REPO_ROOT / "blocks" / "GetWeatherData" / "contract.json"


def test_contract_validator_accepts_get_weather_data():
    v = ContractValidator(SCHEMA_PATH)
    ok, msg = v.validate_contract(SAMPLE_CONTRACT)
    assert ok, msg


def test_contract_validator_rejects_invalid_json(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    v = ContractValidator(SCHEMA_PATH)
    ok, msg = v.validate_contract(bad)
    assert not ok
    assert "Invalid JSON" in msg


def test_contract_validator_rejects_missing_required_field(tmp_path: Path):
    data = json.loads(SAMPLE_CONTRACT.read_text(encoding="utf-8"))
    del data["methodology"]
    p = tmp_path / "contract.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    v = ContractValidator(SCHEMA_PATH)
    ok, msg = v.validate_contract(p)
    assert not ok
    assert "methodology" in msg.lower() or "required" in msg.lower()


def test_contract_pydantic_roundtrip():
    c = Contract.from_json_path(SAMPLE_CONTRACT)
    assert c.block_name == "GetWeatherData"
    assert c.function.name == "get_weather_data"
    assert c.function.return_type == "None"
    assert "OPENWEATHER_API_KEY" in c.required_secrets


def test_block_validator_accepts_get_weather_data():
    bv = BlockValidator()
    ok, errors = bv.validate_structure(REPO_ROOT / "blocks" / "GetWeatherData")
    assert ok, errors


def test_block_validator_missing_src(tmp_path: Path):
    (tmp_path / "contract.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): pass\n", encoding="utf-8")
    bv = BlockValidator()
    ok, errors = bv.validate_structure(tmp_path)
    assert not ok
    assert any("no Python files" in e for e in errors)


def test_block_validator_missing_tests(tmp_path: Path):
    (tmp_path / "contract.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    bv = BlockValidator()
    ok, errors = bv.validate_structure(tmp_path)
    assert not ok
    assert any("no test files" in e for e in errors)


def test_block_validator_not_a_directory(tmp_path: Path):
    f = tmp_path / "file.txt"
    f.write_text("x", encoding="utf-8")
    bv = BlockValidator()
    ok, errors = bv.validate_structure(f)
    assert not ok
    assert any("Not a directory" in e for e in errors)
