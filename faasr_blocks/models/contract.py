"""Pydantic models for FaaSr block contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class FunctionArgument(BaseModel):
    """Single function parameter description."""

    type: str = Field(min_length=1)
    description: str = ""


class S3Output(BaseModel):
    """Declared S3 artifact produced by the block."""

    filename: str = Field(min_length=1)
    format: str = Field(min_length=1)
    description: str = ""


class PythonPackage(BaseModel):
    """PyPI-style dependency pin."""

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)


class ContractMetadata(BaseModel):
    """Discovery and taxonomy fields."""

    role: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    methodology_category: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class ConditionalReturn(BaseModel):
    """When return_type is bool, describes branch semantics."""

    description: str = ""
    true_condition: str = ""
    false_condition: str = ""


class FunctionSpec(BaseModel):
    """Entrypoint name, parameters, and return type."""

    name: str = Field(min_length=1)
    arguments: dict[str, FunctionArgument] = Field(default_factory=dict)
    return_type: Literal["None", "bool"]


class Dependencies(BaseModel):
    """Third-party packages required by the block."""

    python_packages: list[PythonPackage] = Field(default_factory=list)


class Contract(BaseModel):
    """Full block contract aligned with schema/contract_schema.json."""

    block_name: str = Field(min_length=1)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    function: FunctionSpec
    s3_outputs: list[S3Output] = Field(default_factory=list)
    required_secrets: list[str] = Field(default_factory=list)
    preconditions: str = ""
    postconditions: str = ""
    methodology: str = ""
    conditional_return: Optional[ConditionalReturn] = None
    metadata: ContractMetadata
    dependencies: Dependencies

    @classmethod
    def from_json_path(cls, path: Path) -> Contract:
        """Load and parse contract from a JSON file."""
        with path.open(encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        return cls.model_validate(data)
