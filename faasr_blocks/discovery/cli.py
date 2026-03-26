# ruff: noqa: E402

"""CLI for block discovery and embedding management (Phase 3 PoC).

Command-line interface for embedding generation, upload, and semantic search.
Supports two modes:

1. Embed mode: Generate and upload embeddings for blocks
2. Search mode: Query for similar blocks using natural language

Usage:
    faasr-blocks-discover embed [--all | --block BLOCK_NAME]
    faasr-blocks-discover search "fetch weather data from an API"

Environment (all required):
    OPENAI_API_KEY: API key for LLM/embedding access.
    OPENAI_BASE_URL: API endpoint base URL (e.g. https://api.openai.com/v1).
    FAASR_S3_ENDPOINT: S3 endpoint URL.
    FAASR_S3_ACCESS_KEY: S3 access key ID.
    FAASR_S3_SECRET_KEY: S3 secret access key.
    FAASR_S3_BUCKET: S3 bucket name.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import faasr_blocks
from faasr_blocks.builder.config import load_llm_env_config, load_s3_env_config
from faasr_blocks.discovery.embedding import EmbeddingGenerator, OpenAIEmbeddingClient
from faasr_blocks.discovery.search import SqliteVecSearchEngine
from faasr_blocks.discovery.storage import S3EmbeddingStore
from faasr_blocks.models.contract import Contract


def _package_repo_root() -> Path:
    """Repository root for the faasr-blocks package."""
    return Path(faasr_blocks.__file__).resolve().parent.parent


def cmd_embed(args: argparse.Namespace, repo_root: Path) -> int:
    """
    Generate and upload embeddings for blocks.

    Args:
        args: Parsed command-line arguments.
        repo_root: Repository root path.

    Returns:
        Exit code (0 on success, 1 on error).
    """
    # Load config
    try:
        llm_cfg = load_llm_env_config()
        s3_cfg = load_s3_env_config()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    # Validate blocks directory exists
    blocks_root = repo_root / "blocks"
    if not blocks_root.is_dir():
        print(f"Blocks directory not found: {blocks_root}", file=sys.stderr)
        return 1

    # Initialize the clients and generator
    embedding_client = OpenAIEmbeddingClient(
        api_key=llm_cfg.api_key,
        base_url=llm_cfg.base_url,
        model="text-embedding-3-small",
    )
    generator = EmbeddingGenerator(embedding_client)
    store = S3EmbeddingStore(
        endpoint=s3_cfg.endpoint,
        access_key=s3_cfg.access_key,
        secret_key=s3_cfg.secret_key,
        bucket=s3_cfg.bucket,
    )

    # If the user generates all embeddings
    if args.all:
        # Collect all block directories
        block_dirs = [
            d for d in blocks_root.iterdir() if d.is_dir() and (d / "contract.json").exists()
        ]

        # Exit if no blocks are found
        if not block_dirs:
            print(f"No blocks found in {blocks_root}", file=sys.stderr)
            return 1

        print(f"Generating embeddings for {len(block_dirs)} blocks...")

        # Iterate over all block directories
        for block_dir in block_dirs:
            try:
                # Embed and upload the contract
                contract = Contract.from_json_path(block_dir / "contract.json")
                embedding = generator.generate(contract)
                store.upload(embedding)
                print(f"  ✓ {contract.block_name} (v{contract.version})")
            except Exception as e:
                print(f"  ✗ {block_dir.name}: {e}", file=sys.stderr)

        print("Done.")

        return 0

    # If the user generates an embedding for a specific block
    if args.block:
        # Validate the block directory and contract file exist
        block_dir = blocks_root / args.block
        contract_path = block_dir / "contract.json"
        if not contract_path.exists():
            print(f"Contract not found: {contract_path}", file=sys.stderr)
            return 1

        try:
            # Embed and upload the contract
            contract = Contract.from_json_path(contract_path)
            embedding = generator.generate(contract)
            store.upload(embedding)

            print(
                f"✓ Generated and uploaded embedding for {contract.block_name} (v{contract.version})"
            )
            print(f"  Metadata hash: {embedding.metadata_hash}")
            print(f"  Vector dimensions: {len(embedding.embedding)}")

            return 0
        except Exception as e:
            print(f"Failed: {e}", file=sys.stderr)
            return 1

    print("Must specify --all or --block BLOCK_NAME", file=sys.stderr)

    return 1


def cmd_search(args: argparse.Namespace, repo_root: Path) -> int:
    """
    Search for blocks using natural language query.

    Args:
        args: Parsed command-line arguments.
        repo_root: Repository root path.

    Returns:
        Exit code (0 on success, 1 on error).
    """
    # Load config
    try:
        llm_cfg = load_llm_env_config()
        s3_cfg = load_s3_env_config()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    # Initialize the clients and embedding store
    embedding_client = OpenAIEmbeddingClient(
        api_key=llm_cfg.api_key,
        base_url=llm_cfg.base_url,
        model="text-embedding-3-small",
    )
    store = S3EmbeddingStore(
        endpoint=s3_cfg.endpoint,
        access_key=s3_cfg.access_key,
        secret_key=s3_cfg.secret_key,
        bucket=s3_cfg.bucket,
    )

    print("Loading embeddings from S3...")

    # Download all embeddings from S3
    try:
        embeddings = store.download_all()
    except Exception as e:
        print(f"Failed to load embeddings: {e}", file=sys.stderr)
        return 1

    # Exit if no embeddings are found
    if not embeddings:
        print(
            "No embeddings found in S3. Run 'faasr-blocks-discover embed --all' first.",
            file=sys.stderr,
        )
        return 1

    print(f"Loaded {len(embeddings)} block embeddings.")

    with SqliteVecSearchEngine(embeddings, embedding_client) as search_engine:
        print(f"\nSearching for: {args.query}")
        print("-" * 80)

        try:
            results = search_engine.search(args.query, top_n=args.top_n)
        except Exception as e:
            print(f"Search failed: {e}", file=sys.stderr)
            return 1

        if not results:
            print("No results found.")
            return 0

        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.block_name} (v{result.version})")
            print(f"   Similarity: {result.similarity:.4f}")
            print(f"   Metadata hash: {result.metadata_hash[:16]}...")
            print("\n   Description:")
            for line in result.text.split("\n")[:5]:
                print(f"     {line}")
            if len(result.text.split("\n")) > 5:
                print("     ...")

    return 0


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point for faasr-blocks-discover command.

    Args:
        argv: Command-line arguments (defaults to sys.argv if None).

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        description="Discover and search FaaSr blocks using embeddings and semantic search."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    embed_parser = subparsers.add_parser("embed", help="Generate and upload embeddings for blocks.")
    embed_group = embed_parser.add_mutually_exclusive_group(required=True)
    embed_group.add_argument(
        "--all", action="store_true", help="Generate embeddings for all blocks in blocks/."
    )
    embed_group.add_argument(
        "--block", type=str, help="Generate embedding for a specific block (e.g., GetWeatherData)."
    )

    search_parser = subparsers.add_parser(
        "search", help="Search for blocks using natural language."
    )
    search_parser.add_argument(
        "query", type=str, help="Natural language description of desired block functionality."
    )
    search_parser.add_argument(
        "--top-n", type=int, default=5, help="Number of results to return (default: 5)."
    )

    args = parser.parse_args(argv)
    repo_root = _package_repo_root()

    if args.command == "embed":
        return cmd_embed(args, repo_root)
    elif args.command == "search":
        return cmd_search(args, repo_root)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
