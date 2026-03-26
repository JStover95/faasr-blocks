"""Unit tests for Phase 4a orchestrator CLI (no interactive integration tests)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from faasr_blocks.builder.config import load_llm_env_config, load_s3_env_config
from faasr_blocks.orchestrator.cli import main as cli_main
from faasr_blocks.orchestrator.commands import StubHandler
from faasr_blocks.orchestrator.repl import InteractiveREPL, builtin_help_text
from faasr_blocks.orchestrator.session import OrchestratorSession


@pytest.fixture
def required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Minimal valid env for load_llm_env_config and load_s3_env_config."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("FAASR_S3_ENDPOINT", "https://s3.example.com")
    monkeypatch.setenv("FAASR_S3_ACCESS_KEY", "access")
    monkeypatch.setenv("FAASR_S3_SECRET_KEY", "secret")
    monkeypatch.setenv("FAASR_S3_BUCKET", "bucket")


def test_load_llm_env_config_missing_raises() -> None:
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            load_llm_env_config()


def test_load_s3_env_config_missing_raises(
    required_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FAASR_S3_BUCKET", raising=False)
    with pytest.raises(ValueError, match="FAASR_S3_BUCKET"):
        load_s3_env_config()


def test_cli_main_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli_main(["--help"])
    assert exc_info.value.code == 0


def test_cli_main_missing_config_returns_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def _missing_llm() -> None:
        raise ValueError(
            "Missing or empty required environment variable(s): OPENAI_API_KEY. "
            "Set them before running the builder."
        )

    monkeypatch.setattr("faasr_blocks.orchestrator.cli.load_llm_env_config", _missing_llm)
    code = cli_main([])
    assert code == 2


def test_builtin_help_text_mentions_commands() -> None:
    text = builtin_help_text("")
    assert "/help" in text
    assert "/quit" in text
    assert "/clear" in text


def test_orchestrator_session_roundtrip() -> None:
    s = OrchestratorSession()
    s.add_user_message("hi")
    s.add_assistant_message("hello")
    hist = s.get_history()
    assert len(hist) == 2
    assert hist[0]["role"] == "user"
    s.clear()
    assert s.get_history() == []


def test_stub_handler_appends_assistant(required_env: None) -> None:
    session = OrchestratorSession()
    session.add_user_message("fetch weather")
    h = StubHandler()
    out = h.handle("fetch weather", session)
    assert "Stub response" in out
    hist = session.get_history()
    assert len(hist) == 2
    assert hist[1]["role"] == "assistant"
    assert "SqliteVecSearchEngine" in hist[1]["content"]


def test_interactive_repl_quit_immediately(
    required_env: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """REPL exits on /quit without needing a real TTY."""

    class FakePromptSession:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def prompt(self, *args, **kwargs) -> str:
            return "/quit"

    monkeypatch.setattr(
        "faasr_blocks.orchestrator.repl.PromptSession",
        FakePromptSession,
    )

    llm = load_llm_env_config()
    s3 = load_s3_env_config()
    repl = InteractiveREPL(
        OrchestratorSession(),
        StubHandler(),
        repo_root=tmp_path,
        llm_config=llm,
        s3_config=s3,
        history_file=None,
        multiline=False,
        debug=False,
    )
    repl.run()  # should not hang


def test_interactive_repl_natural_language_stub(
    required_env: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    responses = iter(["describe my workflow", "/quit"])

    class FakePromptSession:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def prompt(self, *args, **kwargs) -> str:
            return next(responses)

    monkeypatch.setattr(
        "faasr_blocks.orchestrator.repl.PromptSession",
        FakePromptSession,
    )

    llm = load_llm_env_config()
    s3 = load_s3_env_config()
    sess = OrchestratorSession()
    repl = InteractiveREPL(
        sess,
        StubHandler(),
        repo_root=tmp_path,
        llm_config=llm,
        s3_config=s3,
        history_file=None,
        multiline=False,
        debug=False,
    )
    repl.run()
    captured = capsys.readouterr()
    assert "Stub response" in captured.out
    assert len(sess.get_history()) == 2
