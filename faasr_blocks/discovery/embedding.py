"""Generate embeddings from block contracts for semantic search.

This module provides an embedding generator that creates vector representations of block
contracts based on their metadata, enabling semantic search and discovery of similar blocks.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx

from faasr_blocks.models.contract import Contract


@dataclass(frozen=True)
class BlockEmbedding:
    """
    Vector embedding of a block's contract with integrity metadata.

    Attributes:
        block_name: Name of the block.
        version: Semantic version of the block contract.
        embedding: Vector representation (list of floats).
        metadata_hash: SHA-256 hash of the contract metadata for integrity checking.
        text: The text that was embedded (for debugging/transparency).
    """

    block_name: str
    version: str
    embedding: list[float]
    metadata_hash: str
    text: str

    def to_json(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "block_name": self.block_name,
            "version": self.version,
            "embedding": self.embedding,
            "metadata_hash": self.metadata_hash,
            "text": self.text,
        }

    @classmethod
    def from_json(cls, data: dict) -> BlockEmbedding:
        """Load from JSON dictionary."""
        return cls(
            block_name=data["block_name"],
            version=data["version"],
            embedding=data["embedding"],
            metadata_hash=data["metadata_hash"],
            text=data["text"],
        )


@runtime_checkable
class EmbeddingClient(Protocol):
    """Protocol for embedding API clients (dependency injection)."""

    def embed(self, text: str) -> list[float]:
        """
        Generate embedding vector from text.

        Args:
            text: Input text to embed.

        Returns:
            Embedding vector as list of floats.

        Raises:
            RuntimeError: If the API call fails.
        """
        ...


class OpenAIEmbeddingClient:
    """
    OpenAI-compatible embeddings API client.

    Uses the /embeddings endpoint to generate vector representations of text.
    Supports OpenAI and compatible providers.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "text-embedding-3-small",
        timeout_s: float = 60.0,
    ) -> None:
        """
        Initialize the embedding client.

        Args:
            api_key: API authentication key.
            base_url: API base URL (no trailing slash required).
            model: Model name for embeddings (default: text-embedding-3-small).
            timeout_s: Request timeout in seconds.
        """
        self._api_key = api_key
        self._base = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_s

    def embed(self, text: str) -> list[float]:
        # Prepare the request payload
        url = f"{self._base}/embeddings"
        payload = {
            "model": self._model,
            "input": text,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # Make the API call
        with httpx.Client(timeout=self._timeout) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        # Extract the embedding
        try:
            return data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected embeddings response: {data!r}") from e


class EmbeddingGenerator:
    """
    Generate embeddings from block contracts.

    Uses the contract's metadata fields to create a semantic text representation,
    then embeds it using an EmbeddingClient.
    """

    def __init__(self, client: EmbeddingClient) -> None:
        """
        Initialize the generator with an embedding client.

        Args:
            client: EmbeddingClient implementation (e.g., OpenAIEmbeddingClient).
        """
        self._client = client

    def generate(self, contract: Contract) -> BlockEmbedding:
        """
        Generate an embedding from a contract's metadata.

        Creates a text representation combining role, data type, methodology,
        tags, preconditions, postconditions, and description. Hashes the metadata
        for integrity checking.

        Args:
            contract: The block contract to embed.

        Returns:
            BlockEmbedding with vector, hash, and metadata.
        """
        text = self._contract_to_text(contract)
        metadata_hash = self._compute_metadata_hash(contract)
        embedding_vector = self._client.embed(text)

        return BlockEmbedding(
            block_name=contract.block_name,
            version=contract.version,
            embedding=embedding_vector,
            metadata_hash=metadata_hash,
            text=text,
        )

    def _contract_to_text(self, contract: Contract) -> str:
        """
        Convert contract metadata into searchable text.

        Combines metadata fields in a natural language format optimized for
        semantic search.

        Args:
            contract: The contract to convert.

        Returns:
            Text representation for embedding.
        """
        parts = [
            f"Role: {contract.metadata.role}",
            f"Data Type: {contract.metadata.data_type}",
            f"Methodology: {contract.metadata.methodology_category}",
        ]

        if contract.metadata.tags:
            parts.append(f"Tags: {', '.join(contract.metadata.tags)}")

        if contract.methodology:
            parts.append(f"Method Description: {contract.methodology}")

        if contract.preconditions:
            parts.append(f"Preconditions: {contract.preconditions}")

        if contract.postconditions:
            parts.append(f"Postconditions: {contract.postconditions}")

        if contract.s3_outputs:
            outputs = [f"{o.filename} ({o.format}): {o.description}" for o in contract.s3_outputs]
            parts.append(f"Outputs: {'; '.join(outputs)}")

        if contract.conditional_return:
            parts.append(f"Conditional: {contract.conditional_return.description}")

        return "\n".join(parts)

    def _compute_metadata_hash(self, contract: Contract) -> str:
        """
        Compute SHA-256 hash of contract metadata for integrity checking.

        Includes all fields that contribute to the embedding text so that
        changes to the contract can be detected.

        Args:
            contract: The contract to hash.

        Returns:
            Hex-encoded SHA-256 hash.
        """
        metadata_dict = {
            "block_name": contract.block_name,
            "version": contract.version,
            "role": contract.metadata.role,
            "data_type": contract.metadata.data_type,
            "methodology_category": contract.metadata.methodology_category,
            "tags": sorted(contract.metadata.tags),
            "methodology": contract.methodology,
            "preconditions": contract.preconditions,
            "postconditions": contract.postconditions,
            "s3_outputs": [
                {
                    "filename": o.filename,
                    "format": o.format,
                    "description": o.description,
                }
                for o in contract.s3_outputs
            ],
            "conditional_return": (
                {
                    "description": contract.conditional_return.description,
                    "true_condition": contract.conditional_return.true_condition,
                    "false_condition": contract.conditional_return.false_condition,
                }
                if contract.conditional_return
                else None
            ),
        }

        json_str = json.dumps(metadata_dict, sort_keys=True)
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()
