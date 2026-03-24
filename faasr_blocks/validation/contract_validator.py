"""Validate block contract.json files against the JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


class ContractValidator:
    """Validate contract instances against schema/contract_schema.json."""

    def __init__(self, schema_path: Path) -> None:
        with schema_path.open(encoding="utf-8") as f:
            schema = json.load(f)
        self._validator = Draft202012Validator(schema)

    def validate_contract(self, contract_path: Path) -> tuple[bool, str]:
        """
        Validate a contract.json file against the schema.

        Returns (is_valid, error_message). error_message is empty when valid.
        """
        try:
            with contract_path.open(encoding="utf-8") as f:
                contract = json.load(f)
            errors = sorted(self._validator.iter_errors(contract), key=lambda e: e.path)
            if errors:
                first = errors[0]
                path = ".".join(str(p) for p in first.path) or "(root)"
                return False, f"{path}: {first.message}"
            return True, ""
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except OSError as e:
            return False, f"Failed to read contract: {e}"
