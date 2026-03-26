"""Semantic block discovery and LLM fit check (Phase 4)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from faasr_blocks.builder.llm import LLMClient
from faasr_blocks.discovery.embedding import EmbeddingClient, EmbeddingGenerator
from faasr_blocks.discovery.search import SqliteVecSearchEngine
from faasr_blocks.discovery.storage import EmbeddingStore
from faasr_blocks.models.contract import Contract


@dataclass
class ReuseCandidate:
    """A discovered block with similarity and LLM judgment."""

    contract: Contract
    similarity: float
    reuse_as_is: bool
    reasoning: str


def _extract_json_object(text: str) -> dict:
    """Parse first JSON object from model output (strip markdown fences)."""
    s = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL)
    if fence:
        s = fence.group(1)
    else:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            s = s[start : end + 1]
    return json.loads(s)


class DiscoveryHandler:
    """
    Lazy-load embeddings from S3 into :class:`SqliteVecSearchEngine`, then search + LLM fit.

    If S3 has no embeddings or download fails, search returns no candidates (caller builds all).
    """

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        embedding_store: EmbeddingStore,
        llm: LLMClient,
        blocks_root: Path,
    ) -> None:
        self._embedding_client = embedding_client
        self._embedding_store = embedding_store
        self._llm = llm
        self._blocks_root = blocks_root
        self._generator = EmbeddingGenerator(embedding_client)
        self._engine: SqliteVecSearchEngine | None = None
        self._engine_initialized = False

    def _ensure_engine(self) -> SqliteVecSearchEngine | None:
        if self._engine_initialized:
            return self._engine
        self._engine_initialized = True
        try:
            embeddings = self._embedding_store.download_all()
        except Exception:  # noqa: BLE001 — PoC: skip discovery on S3 errors
            self._engine = None
            return None
        if not embeddings:
            self._engine = None
            return None
        self._engine = SqliteVecSearchEngine(embeddings, self._embedding_client)
        return self._engine

    def close(self) -> None:
        """Release sqlite-vec resources if an engine was opened."""
        if self._engine is not None:
            self._engine.close()
            self._engine = None
            self._engine_initialized = False

    def _contract_to_query_text(self, contract: Contract) -> str:
        """Reuse embedding text shape for query consistency."""
        return self._generator.contract_text_for_embedding(contract)

    def _load_contract(self, block_name: str) -> Contract | None:
        path = self._blocks_root / block_name / "contract.json"
        if not path.is_file():
            return None
        try:
            return Contract.from_json_path(path)
        except Exception:  # noqa: BLE001
            return None

    def _llm_reuse_decision(self, proposed: Contract, candidate: Contract) -> tuple[bool, str]:
        system = (
            "You decide if an existing FaaSr block contract can be reused as-is for a proposed "
            "contract. Reuse as-is only if the function purpose, inputs/outputs shape, secrets, "
            "and methodology are effectively the same; minor naming differences in arguments "
            "are OK if semantics match. If the proposed step needs different behavior or artifacts, "
            "answer reuse_as_is false. Respond with JSON only: "
            '{"reuse_as_is": true|false, "reasoning": "short explanation"}'
        )
        user = (
            "### Proposed contract (JSON)\n"
            + json.dumps(proposed.model_dump(mode="json"), indent=2)
            + "\n\n### Candidate existing contract (JSON)\n"
            + json.dumps(candidate.model_dump(mode="json"), indent=2)
        )
        raw = self._llm.complete(system, user)
        try:
            data = _extract_json_object(raw)
            ok = bool(data.get("reuse_as_is"))
            reason = str(data.get("reasoning", "")).strip() or ("OK" if ok else "Not a match")
            return ok, reason
        except Exception:  # noqa: BLE001
            return False, "Could not parse reuse decision; treating as no reuse."

    def find_reusable_blocks(self, contract: Contract, top_n: int = 5) -> list[ReuseCandidate]:
        """
        Return ranked candidates with LLM reuse judgment (may be empty).

        Args:
            contract: Proposed step contract.
            top_n: Vector search breadth.

        Returns:
            List of ReuseCandidate ordered by similarity (highest first).
        """
        engine = self._ensure_engine()
        if engine is None:
            return []

        query_text = self._contract_to_query_text(contract)
        try:
            # Do not use ``with engine`` here: context exit closes the DB and breaks reuse.
            hits = engine.search(query_text, top_n=top_n)
        except Exception:  # noqa: BLE001
            return []

        out: list[ReuseCandidate] = []
        for hit in hits:
            cand = self._load_contract(hit.block_name)
            if cand is None:
                continue
            reuse_ok, reasoning = self._llm_reuse_decision(contract, cand)
            out.append(
                ReuseCandidate(
                    contract=cand,
                    similarity=hit.similarity,
                    reuse_as_is=reuse_ok,
                    reasoning=reasoning,
                )
            )
        return out
