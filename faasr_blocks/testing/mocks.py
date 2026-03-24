"""
In-process mocks for FaaSr client stubs used in block unit tests.

Patch the symbol where it is *used* (e.g. ``get_weather_data.faasr_put_file``).
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from unittest.mock import patch


class MockFactoryContext(ABC):
    """Context manager that patches a single stub with ``side_effect = self``."""

    def __init__(self, import_path: str) -> None:
        self._import_path = import_path
        self._patch: patch | None = None

    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Behave as the mocked callable."""
        raise NotImplementedError

    def __enter__(self) -> MockFactoryContext:
        # Blocks only import the stubs they use; still patch the full set so the harness is uniform.
        self._patch = patch(self._import_path, create=True)
        mock = self._patch.start()
        mock.side_effect = self
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            if self._patch is not None:
                self._patch.stop()
        finally:
            self.clear()

    @abstractmethod
    def clear(self) -> None:
        """Reset state for the next test."""
        raise NotImplementedError


class MockFaaSrGetFile(MockFactoryContext):
    """``faasr_get_file`` — copy from ``fixtures_dir`` using ``remote_folder`` / ``remote_file``."""

    def __init__(self, import_path: str, fixtures_dir: Path) -> None:
        super().__init__(import_path)
        self.fixtures_dir = fixtures_dir

    def __call__(
        self,
        local_file,
        remote_file,
        server_name="",
        local_folder=".",
        remote_folder=".",
    ):
        rel = Path(remote_folder) / remote_file if remote_folder not in (".", "") else Path(remote_file)
        fixture_path = self.fixtures_dir / rel
        if not fixture_path.is_file():
            # Also try flat name under fixtures (common layout)
            flat = self.fixtures_dir / remote_file
            if flat.is_file():
                fixture_path = flat
            else:
                raise FileNotFoundError(f"Fixture not found: {rel} (or {remote_file})")

        dest = Path(local_folder) / local_file
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(fixture_path, dest)
        return True

    def clear(self) -> None:
        pass


class MockFaaSrPutFile(MockFactoryContext):
    """``faasr_put_file`` — copy local file into ``output_dir`` and record uploads."""

    def __init__(self, import_path: str, output_dir: Path) -> None:
        super().__init__(import_path)
        self.output_dir = output_dir
        self.uploaded_files: list[dict[str, Any]] = []

    def __call__(
        self,
        local_file,
        remote_file,
        server_name="",
        local_folder=".",
        remote_folder=".",
    ):
        src = Path(local_folder) / local_file
        if not src.is_file():
            raise FileNotFoundError(f"Local file not found: {src}")

        rf = str(remote_folder).strip()
        if rf in ("", "."):
            dest = self.output_dir / remote_file
        else:
            dest = self.output_dir / rf / remote_file
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)

        self.uploaded_files.append(
            {
                "local_file": local_file,
                "remote_file": remote_file,
                "remote_folder": remote_folder,
                "dest_path": dest,
            }
        )
        return True

    def clear(self) -> None:
        self.uploaded_files.clear()


class MockFaaSrDeleteFile(MockFactoryContext):
    """``faasr_delete_file`` — record deletions."""

    def __init__(self, import_path: str) -> None:
        super().__init__(import_path)
        self.deleted_files: list[dict[str, str]] = []

    def __call__(self, remote_file, server_name="", remote_folder=""):
        self.deleted_files.append(
            {"remote_file": str(remote_file), "remote_folder": str(remote_folder)}
        )
        return True

    def clear(self) -> None:
        self.deleted_files.clear()


class MockFaaSrLog(MockFactoryContext):
    """``faasr_log`` — append messages."""

    def __init__(self, import_path: str) -> None:
        super().__init__(import_path)
        self.log_messages: list[str] = []

    def __call__(self, log_message):
        if not log_message:
            raise ValueError("Empty log message")
        self.log_messages.append(str(log_message))
        return True

    def clear(self) -> None:
        self.log_messages.clear()


class MockFaaSrGetFolderList(MockFactoryContext):
    """``faasr_get_folder_list`` — return filtered folder names."""

    def __init__(self, import_path: str) -> None:
        super().__init__(import_path)
        self.folders: list[str] = []

    def __call__(self, server_name="", prefix=""):
        p = str(prefix)
        return [f for f in self.folders if f.startswith(p)]

    def with_folders(self, folders: list[str]) -> MockFaaSrGetFolderList:
        self.folders = list(folders)
        return self

    def clear(self) -> None:
        self.folders.clear()


class MockFaaSrRank(MockFactoryContext):
    """``faasr_rank`` — return rank dict like the RPC stub."""

    def __init__(self, import_path: str) -> None:
        super().__init__(import_path)
        self.rank = 0
        self.max_rank = 1

    def __call__(self):
        return {"rank": self.rank, "max_rank": self.max_rank}

    def with_rank(self, rank: int, max_rank: int) -> MockFaaSrRank:
        self.rank = rank
        self.max_rank = max_rank
        return self

    def clear(self) -> None:
        self.rank = 0
        self.max_rank = 1


class MockFaaSrGetS3Creds(MockFactoryContext):
    """``faasr_get_s3_creds`` — return a fake credential dict."""

    def __init__(self, import_path: str) -> None:
        super().__init__(import_path)
        self.creds: dict[str, str] = {
            "access_key": "test-access",
            "secret_key": "test-secret",
            "endpoint": "https://example.invalid",
        }

    def __call__(self):
        return dict(self.creds)

    def with_creds(self, creds: dict[str, str]) -> MockFaaSrGetS3Creds:
        self.creds = dict(creds)
        return self

    def clear(self) -> None:
        self.creds = {
            "access_key": "test-access",
            "secret_key": "test-secret",
            "endpoint": "https://example.invalid",
        }


class MockFaaSrSecret(MockFactoryContext):
    """``faasr_secret`` — in-memory secret store."""

    def __init__(self, import_path: str) -> None:
        super().__init__(import_path)
        self._secret_store: dict[str, str] = {}

    def __call__(self, secret_name: str) -> str:
        if not secret_name:
            raise ValueError("Empty secret name")
        if secret_name not in self._secret_store:
            raise KeyError(f"Secret not found: {secret_name}")
        return self._secret_store[secret_name]

    def with_secret(self, key: str, value: str) -> MockFaaSrSecret:
        self._secret_store[key] = value
        return self

    def clear(self) -> None:
        self._secret_store.clear()


class MockFaaSrInvocationId(MockFactoryContext):
    """``faasr_invocation_id`` — return a fixed test id unless overridden."""

    def __init__(self, import_path: str) -> None:
        super().__init__(import_path)
        self.invocation_id = "test-invocation-id"

    def __call__(self):
        return self.invocation_id

    def with_invocation_id(self, invocation_id: str) -> MockFaaSrInvocationId:
        self.invocation_id = invocation_id
        return self

    def clear(self) -> None:
        self.invocation_id = "test-invocation-id"


class MockFaaSrReturn(MockFactoryContext):
    """``faasr_return`` — record value without exiting the process."""

    def __init__(self, import_path: str) -> None:
        super().__init__(import_path)
        self.return_value: Any = None

    def __call__(self, return_value=None):
        self.return_value = return_value
        return True

    def clear(self) -> None:
        self.return_value = None


class MockFaaSrExit(MockFactoryContext):
    """``faasr_exit`` — record exit payload without calling ``sys.exit``."""

    def __init__(self, import_path: str) -> None:
        super().__init__(import_path)
        self.last_call: dict[str, Any] | None = None

    def __call__(self, message=None, error=True, traceback=None):
        self.last_call = {
            "message": message,
            "error": error,
            "traceback": traceback,
        }
        return True

    def clear(self) -> None:
        self.last_call = None
