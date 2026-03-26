"""Interactive REPL using prompt_toolkit (Phase 4a PoC)."""

from __future__ import annotations

import sys
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import print_formatted_text

from faasr_blocks.builder.config import LLMEnvConfig, S3EnvConfig
from faasr_blocks.orchestrator.commands import CommandHandler
from faasr_blocks.orchestrator.session import OrchestratorSession


def builtin_help_text(multiline_hint: str) -> str:
    """Return /help body (plain text)."""
    return (
        "Commands:\n"
        "  /help     Show this help\n"
        "  /clear    Clear conversation history\n"
        "  /quit     Exit the agent\n"
        "\n"
        "Anything else is treated as a natural-language workflow request (stub response).\n"
        f"{multiline_hint}"
    )


class InteractiveREPL:
    """
    Run the interactive prompt loop until /quit or EOF.

    Slash commands: /help, /clear, /quit. Natural language is delegated to ``handler``.
    """

    def __init__(
        self,
        session: OrchestratorSession,
        handler: CommandHandler,
        *,
        repo_root: Path,
        llm_config: LLMEnvConfig,
        s3_config: S3EnvConfig,
        history_file: Path | None = None,
        multiline: bool = False,
        debug: bool = False,
    ) -> None:
        self._session = session
        self._handler = handler
        self._repo_root = repo_root
        self._llm_config = llm_config
        self._s3_config = s3_config
        self._history_file = history_file
        self._multiline = multiline
        self._debug = debug

    def _make_session(self) -> PromptSession:
        """Initialize the prompt session."""

        # Initialize the history if any exists
        if self._history_file is not None:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            history: FileHistory | InMemoryHistory = FileHistory(str(self._history_file))
        else:
            history = InMemoryHistory()

        key_bindings = None

        # Initialize enter/escape key bindings if multiline is enabled
        if self._multiline:
            bindings = KeyBindings()

            @bindings.add("escape", "enter")
            def _submit_multiline(event) -> None:
                event.current_buffer.validate_and_handle()

            key_bindings = bindings

        return PromptSession(
            history=history,
            multiline=self._multiline,
            key_bindings=key_bindings,
        )

    def _print_welcome(self) -> None:
        """Print the welcome message."""

        print_formatted_text(
            HTML(
                "<b>FaaSr Blocks Agent</b> <ansiyellow>(Phase 4a PoC)</ansiyellow>\n"
                "Type a workflow description, or <b>/help</b> for commands. <b>/quit</b> to exit."
            )
        )
        if self._multiline:
            print_formatted_text(
                HTML(
                    "<ansibrightblack>Multiline: Esc+Enter submits; Enter inserts a newline.</ansibrightblack>"
                )
            )
        print()

    def _debug_line(self, msg: str) -> None:
        """Print a debug message if debug is enabled."""
        if self._debug:
            print(f"[debug] {msg}", file=sys.stderr)

    def run(self) -> None:
        """Run the REPL until user quits or raises KeyboardInterrupt."""

        # Print welcome message and debug information
        self._print_welcome()
        self._debug_line(f"repo_root={self._repo_root}")
        self._debug_line(f"llm base_url={self._llm_config.base_url} model={self._llm_config.model}")
        self._debug_line(f"s3 bucket={self._s3_config.bucket} endpoint={self._s3_config.endpoint}")
        multiline_hint = (
            "Multiline: Esc+Enter submits when --multiline is set.\n" if self._multiline else ""
        )

        # Initialize the prompt session
        pt_session = self._make_session()

        # Run the REPL until user quits or raises KeyboardInterrupt
        while True:
            # Prompt the user for input
            try:
                line = pt_session.prompt("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                return

            # Skip empty lines
            if not line:
                continue

            # Exit if the user quits
            if line == "/quit":
                print("Goodbye!")
                return

            # Print the help text
            if line == "/help":
                print(builtin_help_text(multiline_hint))
                continue

            # Clear the session
            if line == "/clear":
                self._session.clear()
                print_formatted_text(HTML("<ansigreen>Session cleared.</ansigreen>"))
                continue

            # Handle unknown commands
            if line.startswith("/"):
                print_formatted_text(
                    HTML(f"<ansired>Unknown command: {line}</ansired> (try <b>/help</b>)")
                )
                continue

            # Add the user message to the session
            self._session.add_user_message(line)

            # Handle the user message
            try:
                reply = self._handler.handle(line, self._session)
            except Exception as e:
                print_formatted_text(HTML(f"<ansired>Error: {e!s}</ansired>"))
                self._session.add_assistant_message(f"Error: {e!s}")
                continue

            # Print the reply
            print()
            print(reply)
            print()
