"""Load required builder configuration from the environment (fail-fast)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMEnvConfig:
    """OpenAI-compatible API settings required to run the block builder."""

    api_key: str
    base_url: str
    model: str


@dataclass(frozen=True)
class S3EnvConfig:
    """S3-compatible storage settings for embedding storage."""

    endpoint: str
    access_key: str
    secret_key: str
    bucket: str


def load_llm_env_config() -> LLMEnvConfig:
    """
    Read LLM-related environment variables. All are required; missing values raise ValueError.

    Returns:
        LLMEnvConfig with api_key, base_url, and model.

    Raises:
        ValueError: If any required variable is missing or empty, with a list of names.
    """
    required = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "").strip(),
        "OPENAI_BASE_URL": os.environ.get("OPENAI_BASE_URL", "").strip(),
        "OPENAI_MODEL": os.environ.get("OPENAI_MODEL", "").strip(),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(
            f"Missing or empty required environment variable(s): {joined}. "
            "Set them before running the builder."
        )
    return LLMEnvConfig(
        api_key=required["OPENAI_API_KEY"],
        base_url=required["OPENAI_BASE_URL"],
        model=required["OPENAI_MODEL"],
    )


def load_s3_env_config() -> S3EnvConfig:
    """
    Read S3-related environment variables. All are required; missing values raise ValueError.

    Returns:
        S3EnvConfig with endpoint, access_key, secret_key, and bucket.

    Raises:
        ValueError: If any required variable is missing or empty, with a list of names.
    """
    required = {
        "FAASR_S3_ENDPOINT": os.environ.get("FAASR_S3_ENDPOINT", "").strip(),
        "FAASR_S3_ACCESS_KEY": os.environ.get("FAASR_S3_ACCESS_KEY", "").strip(),
        "FAASR_S3_SECRET_KEY": os.environ.get("FAASR_S3_SECRET_KEY", "").strip(),
        "FAASR_S3_BUCKET": os.environ.get("FAASR_S3_BUCKET", "").strip(),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(
            f"Missing or empty required environment variable(s): {joined}. "
            "Set them before running discovery/embedding tools."
        )
    return S3EnvConfig(
        endpoint=required["FAASR_S3_ENDPOINT"],
        access_key=required["FAASR_S3_ACCESS_KEY"],
        secret_key=required["FAASR_S3_SECRET_KEY"],
        bucket=required["FAASR_S3_BUCKET"],
    )
