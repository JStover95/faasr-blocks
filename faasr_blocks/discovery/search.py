"""Vector search engine for block discovery.

This module provides an in-memory vector database using sqlite-vec for fast
semantic search over block embeddings. On initialization, it loads embeddings
from storage and builds an indexed vector table for efficient similarity queries.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Self, runtime_checkable

import sqlite_vec

from faasr_blocks.discovery.embedding import BlockEmbedding, EmbeddingClient


@dataclass
class SearchResult:
    """
    A single search result with block metadata and similarity score.

    Attributes:
        block_name: Name of the matching block.
        version: Version of the matching block.
        similarity: Cosine similarity score (higher is more similar).
        text: The embedded text (for inspection).
        metadata_hash: Hash for integrity checking.
    """

    block_name: str
    version: str
    similarity: float
    text: str
    metadata_hash: str


@runtime_checkable
class BlockSearchEngine(Protocol):
    """Protocol for block search engines (dependency injection).

    Implementations should support use as a context manager so SQLite resources
    are released on exit; callers use ``with engine as e: ...`` instead of
    manual ``close()``.
    """

    def __enter__(self) -> BlockSearchEngine:
        """Enter context; return self for ``with`` binding."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context; release backing resources (e.g. close DB connection)."""
        ...

    def search(self, query_text: str, top_n: int = 10) -> list[SearchResult]:
        """
        Search for blocks semantically similar to the query.

        Args:
            query_text: Natural language description of desired block functionality.
            top_n: Maximum number of results to return.

        Returns:
            List of SearchResult ordered by similarity (most similar first).
        """
        ...

    def get_embedding(self, block_name: str) -> BlockEmbedding | None:
        """
        Retrieve the stored embedding for a specific block.

        Args:
            block_name: Name of the block.

        Returns:
            BlockEmbedding if found, None otherwise.
        """
        ...


class SqliteVecSearchEngine:
    """
    In-memory vector search engine using sqlite-vec.

    Loads all embeddings into an in-memory SQLite database with the vec0 extension
    for efficient cosine similarity searches.
    """

    def __init__(
        self,
        embeddings: list[BlockEmbedding],
        embedding_client: EmbeddingClient,
    ) -> None:
        """
        Initialize the search engine with pre-loaded embeddings.

        Args:
            embeddings: List of block embeddings to index.
            embedding_client: Client for embedding query text.
        """
        self._embedding_client = embedding_client
        self._embeddings_by_name = {e.block_name: e for e in embeddings}
        self._conn: sqlite3.Connection | None = self._build_index(embeddings)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def _build_index(self, embeddings: list[BlockEmbedding]) -> sqlite3.Connection:
        """
        Create an in-memory SQLite database and populate with embeddings.

        Args:
            embeddings: List of embeddings to index.

        Returns:
            SQLite connection with vec0 extension loaded.
        """
        # Connect to an in-memory SQLite database
        conn = sqlite3.connect(":memory:")
        conn.enable_load_extension(True)

        # Load the sqlite-vec extension
        try:
            sqlite_vec.load(conn)
        except Exception as e:
            raise RuntimeError(
                "Failed to load sqlite-vec extension. Install sqlite-vec: pip install sqlite-vec"
            ) from e

        # If no embeddings are provided, return early
        if not embeddings:
            return conn

        # Create the virtual table
        dimension = len(embeddings[0].embedding)
        conn.execute(
            f"""
            CREATE VIRTUAL TABLE embeddings USING vec0(
                block_name TEXT PRIMARY KEY,
                version TEXT,
                metadata_hash TEXT,
                text TEXT,
                embedding FLOAT[{dimension}]
            )
            """
        )

        # Insert the embeddings
        for emb in embeddings:
            conn.execute(
                """
                INSERT INTO embeddings (block_name, version, metadata_hash, text, embedding)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    emb.block_name,
                    emb.version,
                    emb.metadata_hash,
                    emb.text,
                    json_array_to_blob(emb.embedding),
                ),
            )

        # Commit the transaction
        conn.commit()

        return conn

    def search(self, query_text: str, top_n: int = 10) -> list[SearchResult]:
        # Exit if the database is closed
        if self._conn is None:
            raise RuntimeError("SqliteVecSearchEngine is closed")

        # Generate the query embedding
        query_embedding = self._embedding_client.embed(query_text)

        # Execute the search query
        cursor = self._conn.execute(
            """
            SELECT
                block_name,
                version,
                text,
                metadata_hash,
                distance
            FROM embeddings
            WHERE embedding MATCH ?
            ORDER BY distance
            LIMIT ?
            """,
            (json_array_to_blob(query_embedding), top_n),
        )

        # Build the results array
        results = []
        for row in cursor.fetchall():
            block_name, version, text, metadata_hash, distance = row
            similarity = 1.0 - distance
            results.append(
                SearchResult(
                    block_name=block_name,
                    version=version,
                    similarity=similarity,
                    text=text,
                    metadata_hash=metadata_hash,
                )
            )

        return results

    def get_embedding(self, block_name: str) -> BlockEmbedding | None:
        return self._embeddings_by_name.get(block_name)

    def close(self) -> None:
        """Close the database connection. Idempotent; safe after context exit."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def json_array_to_blob(arr: list[float]) -> bytes:
    """
    Convert a list of floats to a binary blob for sqlite-vec.

    Args:
        arr: List of floats representing the embedding vector.

    Returns:
        Binary representation for SQLite storage.
    """
    import struct

    return struct.pack(f"{len(arr)}f", *arr)
