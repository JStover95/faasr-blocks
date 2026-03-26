"""Dispatch BlockBuilder and upload embeddings after successful builds (Phase 4)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from faasr_blocks.builder.block_builder import BlockBuilder
from faasr_blocks.builder.block_context import BlockContext
from faasr_blocks.builder.llm import LLMClient
from faasr_blocks.builder.models import BuildResult
from faasr_blocks.builder.source_generator import SourceCodeGenerator
from faasr_blocks.builder.test_generator import TestGenerator
from faasr_blocks.builder.test_validator import ContractTestCoverageValidator
from faasr_blocks.discovery.embedding import EmbeddingGenerator
from faasr_blocks.discovery.storage import EmbeddingStore
from faasr_blocks.models.contract import Contract


@dataclass
class BuildDispatchResult:
    """Outcome of orchestrator-driven block build + optional embedding upload."""

    contract: Contract
    build_result: BuildResult
    embedding_uploaded: bool = False
    embedding_error: str = ""


class BuilderDispatcher:
    """
    Create block directory, write contract.json, run :class:`BlockBuilder`, upload embedding.

    On build success, generates an embedding from the contract and uploads via ``embedding_store``.
    """

    def __init__(
        self,
        llm: LLMClient,
        embedding_generator: EmbeddingGenerator,
        embedding_store: EmbeddingStore,
        repo_root: Path,
        schema_path: Path,
        *,
        max_source_iterations: int = 3,
    ) -> None:
        self._llm = llm
        self._embedding_generator = embedding_generator
        self._embedding_store = embedding_store
        self._repo_root = repo_root
        self._schema_path = schema_path
        self._max_source_iterations = max_source_iterations

    def _write_contract(self, block_path: Path, contract: Contract) -> None:
        block_path.mkdir(parents=True, exist_ok=True)
        (block_path / "src").mkdir(exist_ok=True)
        (block_path / "tests").mkdir(exist_ok=True)
        (block_path / "tests" / "fixtures").mkdir(exist_ok=True)
        data = contract.model_dump(mode="json")
        (block_path / "contract.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def build_block(self, contract: Contract) -> BuildDispatchResult:
        """
        Build a single block from a contract (writes files under ``blocks/<BlockName>/``).

        Args:
            contract: Fully specified contract.

        Returns:
            BuildDispatchResult with build outcome and embedding upload status.
        """
        blocks_root = self._repo_root / "blocks"
        block_path = blocks_root / contract.block_name
        self._write_contract(block_path, contract)

        context = BlockContext(
            contract=contract,
            block_path=block_path,
            repo_root=self._repo_root,
            schema_path=self._schema_path,
        )

        test_generator = TestGenerator(self._llm, context)
        test_coverage_validator = ContractTestCoverageValidator(self._llm, context)
        source_generator = SourceCodeGenerator(self._llm, context)

        builder = BlockBuilder(
            context=context,
            test_generator=test_generator,
            test_coverage_validator=test_coverage_validator,
            source_generator=source_generator,
            max_source_iterations=self._max_source_iterations,
        )

        build_result = builder.build()

        embedding_uploaded = False
        embedding_error = ""
        if build_result.success:
            try:
                emb = self._embedding_generator.generate(contract)
                self._embedding_store.upload(emb)
                embedding_uploaded = True
            except Exception as e:  # noqa: BLE001 — PoC: surface error in summary
                embedding_error = str(e)

        return BuildDispatchResult(
            contract=contract,
            build_result=build_result,
            embedding_uploaded=embedding_uploaded,
            embedding_error=embedding_error,
        )
