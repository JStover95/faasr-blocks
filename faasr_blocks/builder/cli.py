# ruff: noqa: E402

"""CLI for building a block from contract.json (Phase 2 PoC).

Command-line interface for the block builder. Takes an existing block directory
(containing contract.json) and generates tests and implementation using an OpenAI-compatible LLM.

Usage:
    faasr-blocks-build path/to/blocks/BlockName

Environment (all required):
    OPENAI_API_KEY: API key for LLM access.
    OPENAI_BASE_URL: API endpoint base URL (e.g. https://api.openai.com/v1).
    OPENAI_MODEL: Model name for chat completions.
    FAASR_BLOCKS_DEBUG: Optional. Set to "1" for verbose debug output.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import faasr_blocks
from faasr_blocks.builder.block_builder import BlockBuilder
from faasr_blocks.builder.config import load_llm_env_config
from faasr_blocks.builder.llm import OpenAIChatLLM
from faasr_blocks.builder.source_generator import SourceCodeGenerator
from faasr_blocks.builder.static_validator import StaticValidator
from faasr_blocks.builder.test_generator import TestGenerator
from faasr_blocks.builder.test_runner import TestRunner
from faasr_blocks.builder.test_validator import ContractTestCoverageValidator
from faasr_blocks.models.contract import Contract
from faasr_blocks.validation.block_validator import BlockValidator


def _package_repo_root() -> Path:
    """Repository root for the faasr-blocks package (parent of the ``faasr_blocks`` package)."""
    return Path(faasr_blocks.__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point for faasr-blocks-build command.

    Parses arguments, loads configuration and contract, builds dependencies, and invokes BlockBuilder.

    Args:
        argv: Command-line arguments (defaults to sys.argv if None).

    Returns:
        Exit code: 0 on success, 1 on build failure, 2 on usage/setup errors.
    """
    parser = argparse.ArgumentParser(
        description="Generate tests and source for a FaaSr block from an existing block directory "
        "(requires OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL).",
    )
    parser.add_argument(
        "block_dir",
        type=Path,
        help="Path to the block directory (must contain contract.json), e.g. blocks/GetWeatherData.",
    )
    parser.add_argument(
        "--max-source-iterations",
        type=int,
        default=3,
        help="Max fix-up loops for static validation / pytest failures.",
    )
    args = parser.parse_args(argv)

    repo_root = _package_repo_root()
    blocks_root = repo_root / "blocks"
    schema_path = (repo_root / "schema" / "contract_schema.json").resolve()
    block_path = args.block_dir.resolve()

    if not block_path.is_dir():
        print(f"Block directory not found or not a directory: {block_path}", file=sys.stderr)
        return 2

    contract_path = block_path / "contract.json"
    if not contract_path.is_file():
        print(f"contract.json not found in block directory: {contract_path}", file=sys.stderr)
        return 2

    if not schema_path.is_file():
        print(
            f"Contract schema not found (expected at {schema_path}). "
            "Ensure the faasr-blocks repo layout includes schema/contract_schema.json.",
            file=sys.stderr,
        )
        return 2

    try:
        llm_cfg = load_llm_env_config()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    contract = Contract.from_json_path(contract_path)

    llm = OpenAIChatLLM(
        api_key=llm_cfg.api_key,
        base_url=llm_cfg.base_url,
        model=llm_cfg.model,
    )
    test_generator = TestGenerator(llm)
    test_coverage_validator = ContractTestCoverageValidator(llm)
    source_generator = SourceCodeGenerator(llm)
    static_validator = StaticValidator()
    test_runner = TestRunner()
    block_validator = BlockValidator()

    builder = BlockBuilder(
        schema_path=schema_path,
        test_generator=test_generator,
        test_coverage_validator=test_coverage_validator,
        source_generator=source_generator,
        static_validator=static_validator,
        test_runner=test_runner,
        block_validator=block_validator,
        max_source_iterations=args.max_source_iterations,
    )

    print(f"Repo root: {repo_root}")
    print(f"Blocks root: {blocks_root}")
    print(f"Building block: {contract.block_name}")
    try:
        result = builder.build(contract, block_path)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2

    print()
    if result.success:
        print(result.message)
        print(f"Block path: {result.block_path}")
        if result.test_result:
            print(f"Pytest: {result.test_result.summary_line}")
        return 0

    print(f"FAILED: {result.message}", file=sys.stderr)
    if result.test_contract_validation and not result.test_contract_validation.ok:
        for e in result.test_contract_validation.errors:
            print(f"  test-contract: {e}", file=sys.stderr)
    if result.static_validation and not result.static_validation.ok:
        for e in result.static_validation.errors:
            print(f"  static: {e}", file=sys.stderr)
    if result.test_result and not result.test_result.passed:
        print(result.test_result.stdout[-4000:], file=sys.stderr)
        print(result.test_result.stderr[-2000:], file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
