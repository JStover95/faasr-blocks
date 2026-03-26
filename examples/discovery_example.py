"""Example: Generate embeddings and search for similar blocks.

This demonstrates the Phase 3 discovery API usage programmatically.
Run this after setting environment variables for OpenAI API and S3.
"""

from __future__ import annotations

from pathlib import Path

from faasr_blocks.builder.config import load_llm_env_config, load_s3_env_config
from faasr_blocks.discovery.embedding import EmbeddingGenerator, OpenAIEmbeddingClient
from faasr_blocks.discovery.search import SqliteVecSearchEngine
from faasr_blocks.discovery.storage import S3EmbeddingStore
from faasr_blocks.models.contract import Contract


def main():
    """Run discovery example."""
    print("=" * 80)
    print("FaaSr Blocks Discovery Example")
    print("=" * 80)

    try:
        llm_cfg = load_llm_env_config()
        s3_cfg = load_s3_env_config()
    except ValueError as e:
        print(f"\nError: {e}")
        print("\nSet these environment variables:")
        print("  OPENAI_API_KEY, OPENAI_BASE_URL")
        print("  FAASR_S3_ENDPOINT, FAASR_S3_ACCESS_KEY, FAASR_S3_SECRET_KEY, FAASR_S3_BUCKET")
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    blocks_root = repo_root / "blocks"

    print(f"\nRepo root: {repo_root}")
    print(f"Blocks root: {blocks_root}")

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

    print("\n" + "=" * 80)
    print("Step 1: Generate Embeddings for All Blocks")
    print("=" * 80)

    block_dirs = [d for d in blocks_root.iterdir() if d.is_dir() and (d / "contract.json").exists()]

    if not block_dirs:
        print(f"\nNo blocks found in {blocks_root}")
        print("Create blocks first using: faasr-blocks-build")
        return 1

    print(f"\nFound {len(block_dirs)} blocks:")
    for block_dir in block_dirs:
        print(f"  - {block_dir.name}")

    print("\nGenerating embeddings...")
    for block_dir in block_dirs:
        try:
            contract = Contract.from_json_path(block_dir / "contract.json")
            embedding = generator.generate(contract)
            store.upload(embedding)
            print(f"  ✓ {contract.block_name} (v{contract.version})")
        except Exception as e:
            print(f"  ✗ {block_dir.name}: {e}")

    print("\n" + "=" * 80)
    print("Step 2: Load Embeddings from S3")
    print("=" * 80)

    print("\nDownloading embeddings from S3...")
    try:
        embeddings = store.download_all()
        print(f"✓ Loaded {len(embeddings)} embeddings")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return 1

    print("\n" + "=" * 80)
    print("Step 3: Build In-Memory Search Index")
    print("=" * 80)

    print("\nInitializing sqlite-vec search engine...")
    search_engine = SqliteVecSearchEngine(embeddings, embedding_client)
    print(f"✓ Indexed {len(embeddings)} blocks for vector search")

    print("\n" + "=" * 80)
    print("Step 4: Semantic Search Examples")
    print("=" * 80)

    queries = [
        "fetch weather data from an API",
        "process JSON time-series data",
        "create visualizations with matplotlib",
    ]

    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 80)
        try:
            results = search_engine.search(query, top_n=3)
            if not results:
                print("  No results found.")
            else:
                for i, result in enumerate(results, 1):
                    print(f"\n  {i}. {result.block_name} (v{result.version})")
                    print(f"     Similarity: {result.similarity:.4f}")
                    first_line = result.text.split("\n")[0] if result.text else ""
                    print(f"     {first_line}")
        except Exception as e:
            print(f"  Search failed: {e}")

    print("\n" + "=" * 80)
    print("Step 5: Retrieve Full Contract")
    print("=" * 80)

    if embeddings:
        example_block = embeddings[0].block_name
        print(f"\nRetrieving contract for: {example_block}")
        contract_path = blocks_root / example_block / "contract.json"
        if contract_path.exists():
            contract = Contract.from_json_path(contract_path)
            print(f"✓ Loaded contract for {contract.block_name}")
            print(f"  Function: {contract.function.name}()")
            print(f"  Role: {contract.metadata.role}")
            print(f"  Data Type: {contract.metadata.data_type}")
            print(f"  S3 Outputs: {len(contract.s3_outputs)}")
            print(f"  Dependencies: {len(contract.dependencies.python_packages)} packages")

    search_engine.close()

    print("\n" + "=" * 80)
    print("Discovery Example Complete")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    exit(main())
