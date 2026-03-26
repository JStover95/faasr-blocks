"""S3 storage for block embeddings.

This module provides utilities for uploading and downloading embedding vectors to/from
S3-compatible storage. Embeddings are stored as JSON files with a consistent naming convention.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, runtime_checkable

import boto3
from botocore.exceptions import ClientError

from faasr_blocks.discovery.embedding import BlockEmbedding


@runtime_checkable
class EmbeddingStore(Protocol):
    """Protocol for embedding storage backends (dependency injection)."""

    def upload(self, embedding: BlockEmbedding) -> None:
        """
        Upload an embedding to storage.

        Args:
            embedding: The embedding to store.

        Raises:
            RuntimeError: If the upload fails.
        """
        ...

    def download(self, block_name: str) -> BlockEmbedding | None:
        """
        Download an embedding from storage.

        Args:
            block_name: Name of the block to retrieve.

        Returns:
            BlockEmbedding if found, None otherwise.

        Raises:
            RuntimeError: If the download fails for reasons other than not found.
        """
        ...

    def list_all(self) -> list[str]:
        """
        List all block names with embeddings in storage.

        Returns:
            List of block names.

        Raises:
            RuntimeError: If listing fails.
        """
        ...

    def download_all(self) -> list[BlockEmbedding]:
        """
        Download all embeddings from storage.

        Returns:
            List of all embeddings.

        Raises:
            RuntimeError: If downloads fail.
        """
        ...


class S3EmbeddingStore:
    """
    S3-backed storage for block embeddings.

    Stores embeddings as JSON files in S3 with the path convention:
    faasr-blocks/embeddings/<BlockName>.json

    Each JSON file contains the embedding vector, metadata hash, and searchable text.
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        prefix: str = "faasr-blocks/embeddings",
    ) -> None:
        """
        Initialize S3 client with credentials.

        Args:
            endpoint: S3 endpoint URL (e.g., https://s3.amazonaws.com).
            access_key: S3 access key ID.
            secret_key: S3 secret access key.
            bucket: S3 bucket name.
            prefix: Key prefix for embeddings (default: faasr-blocks/embeddings).
        """
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")
        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def upload(self, embedding: BlockEmbedding) -> None:
        key = f"{self._prefix}/{embedding.block_name}.json"
        data = json.dumps(embedding.to_json(), indent=2)
        try:
            self._s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data.encode("utf-8"),
                ContentType="application/json",
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to upload embedding for {embedding.block_name}: {e}") from e

    def download(self, block_name: str) -> BlockEmbedding | None:
        key = f"{self._prefix}/{block_name}.json"
        try:
            response = self._s3.get_object(Bucket=self._bucket, Key=key)
            data = json.loads(response["Body"].read().decode("utf-8"))
            return BlockEmbedding.from_json(data)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise RuntimeError(f"Failed to download embedding for {block_name}: {e}") from e

    def list_all(self) -> list[str]:
        try:
            paginator = self._s3.get_paginator("list_objects_v2")
            block_names = []
            for page in paginator.paginate(Bucket=self._bucket, Prefix=f"{self._prefix}/"):
                if "Contents" not in page:
                    continue
                for obj in page["Contents"]:
                    key = obj["Key"]
                    if key.endswith(".json"):
                        filename = Path(key).name
                        block_name = filename.removesuffix(".json")
                        block_names.append(block_name)
            return block_names
        except ClientError as e:
            raise RuntimeError(f"Failed to list embeddings: {e}") from e

    def download_all(self) -> list[BlockEmbedding]:
        block_names = self.list_all()
        embeddings = []
        for name in block_names:
            emb = self.download(name)
            if emb is not None:
                embeddings.append(emb)
        return embeddings


class LocalEmbeddingStore:
    """
    Local filesystem storage for embeddings (for testing/development).

    Stores embeddings in a local directory with the same JSON structure as S3.
    """

    def __init__(self, directory: Path) -> None:
        """
        Initialize local store.

        Args:
            directory: Path to directory for storing embedding JSON files.
        """
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)

    def upload(self, embedding: BlockEmbedding) -> None:
        path = self._dir / f"{embedding.block_name}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(embedding.to_json(), f, indent=2)

    def download(self, block_name: str) -> BlockEmbedding | None:
        path = self._dir / f"{block_name}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return BlockEmbedding.from_json(data)

    def list_all(self) -> list[str]:
        return [p.stem for p in self._dir.glob("*.json")]

    def download_all(self) -> list[BlockEmbedding]:
        embeddings = []
        for path in self._dir.glob("*.json"):
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            embeddings.append(BlockEmbedding.from_json(data))
        return embeddings
