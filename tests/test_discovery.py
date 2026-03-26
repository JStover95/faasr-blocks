"""Unit tests for embedding generation, storage, and search."""

from __future__ import annotations

import tempfile
from pathlib import Path

from faasr_blocks.discovery.embedding import (
    BlockEmbedding,
    EmbeddingGenerator,
)
from faasr_blocks.discovery.search import SqliteVecSearchEngine
from faasr_blocks.discovery.storage import LocalEmbeddingStore
from faasr_blocks.models.contract import (
    Contract,
    ContractMetadata,
    Dependencies,
    FunctionSpec,
    S3Output,
)


def _make_test_contract(
    block_name: str = "TestBlock",
    role: str = "fetch_data",
    data_type: str = "weather",
    methodology_category: str = "api_call",
    tags: list[str] | None = None,
) -> Contract:
    """Factory for test contracts."""
    return Contract(
        block_name=block_name,
        version="1.0.0",
        function=FunctionSpec(name="test_function", arguments={}, return_type="None"),
        s3_outputs=[S3Output(filename="output.json", format="JSON", description="Test output")],
        required_secrets=[],
        preconditions="Test precondition",
        postconditions="Test postcondition",
        methodology="Test methodology",
        conditional_return=None,
        metadata=ContractMetadata(
            role=role,
            data_type=data_type,
            methodology_category=methodology_category,
            tags=tags or ["test"],
        ),
        dependencies=Dependencies(python_packages=[]),
    )


class MockEmbeddingClient:
    """Mock embedding client for testing."""

    def __init__(self, dimension: int = 1536) -> None:
        self._dimension = dimension
        self._call_count = 0

    def embed(self, text: str) -> list[float]:
        self._call_count += 1
        return [float(i) for i in range(self._dimension)]


def test_embedding_generator_creates_embedding():
    """EmbeddingGenerator should create valid embeddings from contracts."""
    contract = _make_test_contract()
    client = MockEmbeddingClient(dimension=8)
    generator = EmbeddingGenerator(client)

    embedding = generator.generate(contract)

    assert embedding.block_name == "TestBlock"
    assert embedding.version == "1.0.0"
    assert len(embedding.embedding) == 8
    assert embedding.metadata_hash
    assert len(embedding.metadata_hash) == 64
    assert "Role: fetch_data" in embedding.text
    assert "Data Type: weather" in embedding.text


def test_embedding_generator_consistent_hash():
    """Same contract should produce same hash."""
    contract = _make_test_contract()
    client = MockEmbeddingClient()
    generator = EmbeddingGenerator(client)

    emb1 = generator.generate(contract)
    emb2 = generator.generate(contract)

    assert emb1.metadata_hash == emb2.metadata_hash


def test_embedding_generator_different_hash_on_change():
    """Different metadata should produce different hash."""
    contract1 = _make_test_contract(block_name="Block1")
    contract2 = _make_test_contract(block_name="Block2")
    client = MockEmbeddingClient()
    generator = EmbeddingGenerator(client)

    emb1 = generator.generate(contract1)
    emb2 = generator.generate(contract2)

    assert emb1.metadata_hash != emb2.metadata_hash


def test_local_embedding_store_roundtrip():
    """LocalEmbeddingStore should persist and retrieve embeddings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalEmbeddingStore(Path(tmpdir))
        embedding = BlockEmbedding(
            block_name="TestBlock",
            version="1.0.0",
            embedding=[1.0, 2.0, 3.0],
            metadata_hash="abc123",
            text="Test text",
        )

        store.upload(embedding)
        retrieved = store.download("TestBlock")

        assert retrieved is not None
        assert retrieved.block_name == "TestBlock"
        assert retrieved.embedding == [1.0, 2.0, 3.0]
        assert retrieved.metadata_hash == "abc123"


def test_local_embedding_store_download_missing():
    """LocalEmbeddingStore should return None for missing blocks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalEmbeddingStore(Path(tmpdir))
        result = store.download("NonExistent")
        assert result is None


def test_local_embedding_store_list_all():
    """LocalEmbeddingStore should list all stored blocks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalEmbeddingStore(Path(tmpdir))

        emb1 = BlockEmbedding("Block1", "1.0.0", [1.0], "hash1", "text1")
        emb2 = BlockEmbedding("Block2", "1.0.0", [2.0], "hash2", "text2")

        store.upload(emb1)
        store.upload(emb2)

        names = store.list_all()
        assert set(names) == {"Block1", "Block2"}


def test_local_embedding_store_download_all():
    """LocalEmbeddingStore should download all embeddings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalEmbeddingStore(Path(tmpdir))

        emb1 = BlockEmbedding("Block1", "1.0.0", [1.0], "hash1", "text1")
        emb2 = BlockEmbedding("Block2", "1.0.0", [2.0], "hash2", "text2")

        store.upload(emb1)
        store.upload(emb2)

        all_embeddings = store.download_all()
        assert len(all_embeddings) == 2
        names = {e.block_name for e in all_embeddings}
        assert names == {"Block1", "Block2"}


def test_sqlite_vec_search_engine_basic_search():
    """SqliteVecSearchEngine should return relevant results."""
    embeddings = [
        BlockEmbedding(
            "WeatherFetch",
            "1.0.0",
            [1.0, 0.0, 0.0],
            "hash1",
            "Role: fetch_data\nData Type: weather",
        ),
        BlockEmbedding(
            "DataProcess",
            "1.0.0",
            [0.0, 1.0, 0.0],
            "hash2",
            "Role: process_data\nData Type: generic",
        ),
    ]

    client = MockEmbeddingClient(dimension=3)
    engine = SqliteVecSearchEngine(embeddings, client)

    results = engine.search("fetch weather", top_n=2)

    assert len(results) <= 2
    assert all(r.block_name in ["WeatherFetch", "DataProcess"] for r in results)
    assert all(isinstance(r.similarity, float) for r in results)

    engine.close()


def test_sqlite_vec_search_engine_get_embedding():
    """SqliteVecSearchEngine should retrieve stored embeddings."""
    embedding = BlockEmbedding("TestBlock", "1.0.0", [1.0, 2.0], "hash", "Test text")
    client = MockEmbeddingClient(dimension=2)
    engine = SqliteVecSearchEngine([embedding], client)

    retrieved = engine.get_embedding("TestBlock")

    assert retrieved is not None
    assert retrieved.block_name == "TestBlock"
    assert retrieved.embedding == [1.0, 2.0]

    engine.close()


def test_sqlite_vec_search_engine_missing_embedding():
    """SqliteVecSearchEngine should return None for missing blocks."""
    client = MockEmbeddingClient(dimension=2)
    engine = SqliteVecSearchEngine([], client)

    result = engine.get_embedding("NonExistent")

    assert result is None
    engine.close()


def test_block_embedding_json_roundtrip():
    """BlockEmbedding should serialize and deserialize correctly."""
    embedding = BlockEmbedding(
        block_name="TestBlock",
        version="1.0.0",
        embedding=[1.0, 2.0, 3.0],
        metadata_hash="abc123",
        text="Test text",
    )

    json_dict = embedding.to_json()
    restored = BlockEmbedding.from_json(json_dict)

    assert restored.block_name == embedding.block_name
    assert restored.version == embedding.version
    assert restored.embedding == embedding.embedding
    assert restored.metadata_hash == embedding.metadata_hash
    assert restored.text == embedding.text
