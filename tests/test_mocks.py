"""Unit tests for FaaSr stub mocks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from faasr_blocks.testing.mocks import MockFaaSrGetFile, MockFaaSrPutFile, MockFaaSrSecret


def test_mock_get_file_flat_fixture(tmp_path: Path):
    fix = tmp_path / "fixtures"
    fix.mkdir()
    (fix / "data.json").write_text('{"a": 1}', encoding="utf-8")
    work = tmp_path / "work"
    work.mkdir()

    with MockFaaSrGetFile("__main__.faasr_get_file", fix) as mock:
        mock("out.json", "data.json", local_folder=str(work))
        dest = work / "out.json"
        assert dest.is_file()
        assert json.loads(dest.read_text(encoding="utf-8")) == {"a": 1}


def test_mock_put_file_nested_remote_folder(tmp_path: Path):
    out_root = tmp_path / "s3"

    with MockFaaSrPutFile("__main__.faasr_put_file", out_root) as m:
        local = tmp_path / "local.txt"
        local.write_text("hello", encoding="utf-8")
        m("local.txt", "remote.txt", local_folder=str(tmp_path), remote_folder="ns1")
        dest = out_root / "ns1" / "remote.txt"
        assert dest.read_text(encoding="utf-8") == "hello"
        assert len(m.uploaded_files) == 1


def test_mock_secret_missing_raises():
    with MockFaaSrSecret("__main__.faasr_secret") as m:
        with pytest.raises(KeyError):
            m("ANY")
