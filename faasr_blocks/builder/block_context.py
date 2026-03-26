"""Shared context for block build pipeline (single source of truth for paths and contract)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from faasr_blocks.models.contract import Contract


@dataclass
class BlockContext:
    """Centralized context for block building operations."""

    contract: Contract
    block_path: Path
    repo_root: Path
    schema_path: Path

    @property
    def function_name(self) -> str:
        """Function name from contract."""
        return self.contract.function.name

    @property
    def block_name(self) -> str:
        """Block name from contract."""
        return self.contract.block_name

    @property
    def test_path(self) -> Path:
        """Path to primary test file."""
        return self.block_path / "tests" / f"test_{self.function_name}.py"

    @property
    def src_file(self) -> Path:
        """Path to source implementation file."""
        return self.block_path / "src" / f"{self.function_name}.py"

    @property
    def contract_path(self) -> Path:
        """Path to contract.json."""
        return self.block_path / "contract.json"

    @property
    def blocks_root(self) -> Path:
        """Blocks directory (parent of block_path)."""
        return self.block_path.parent
