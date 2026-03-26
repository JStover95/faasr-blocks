"""Markdown workflow summary for Phase 4 orchestrator."""

from __future__ import annotations

from faasr_blocks.builder.models import BuildResult
from faasr_blocks.models.contract import Contract


def _function_signature(c: Contract) -> str:
    """Build a short ``name(arg: type, ...)`` string from the contract."""
    args = c.function.arguments
    if not args:
        return f"{c.function.name}()"
    parts = [f"{name}: {spec.type}" for name, spec in args.items()]
    return f"{c.function.name}({', '.join(parts)})"


def _outputs_line(c: Contract) -> str:
    """Describe S3 outputs as bullet-friendly text."""
    if not c.s3_outputs:
        return "(none declared)"
    lines = []
    for o in c.s3_outputs:
        lines.append(f"{o.filename} ({o.format})")
    return "; ".join(lines)


def _contract_one_liner(c: Contract) -> str:
    """Short NL summary for a new block."""
    return (c.methodology or c.postconditions or c.metadata.role).strip() or c.block_name


def format_workflow_summary(
    user_request: str,
    reused_blocks: list[tuple[Contract, str]],
    new_blocks: list[tuple[Contract, BuildResult]],
    workflow_dag: list[tuple[str, str]],
    *,
    blocks_root_display: str = "blocks/",
) -> str:
    """
    Format a human-readable markdown summary of the workflow outcome.

    Args:
        user_request: Original natural-language request.
        reused_blocks: Pairs of (contract, reasoning) for reused blocks.
        new_blocks: Pairs of (contract, build result) for newly built blocks.
        workflow_dag: Directed edges (from_block_name, to_block_name).
        blocks_root_display: Relative path hint for next steps.

    Returns:
        Markdown string.
    """
    lines: list[str] = [
        "## Workflow summary",
        "",
        f"**Request:** {user_request.strip()}",
        "",
        "### Blocks",
        "",
    ]

    idx = 1
    for contract, reasoning in reused_blocks:
        lines.append(
            f"{idx}. **{contract.block_name}** (reused) — _{contract.metadata.role}_",
        )
        lines.append(f"   - **Why:** {reasoning.strip()}")
        lines.append(f"   - **Function:** `{_function_signature(contract)}`")
        lines.append(f"   - **Outputs:** {_outputs_line(contract)}")
        lines.append("")
        idx += 1

    for contract, result in new_blocks:
        status = "built" if result.success else "build failed"
        lines.append(
            f"{idx}. **{contract.block_name}** (new, {status}) — _{contract.metadata.role}_",
        )
        lines.append(f"   - **Contract:** {_contract_one_liner(contract)}")
        lines.append(f"   - **Function:** `{_function_signature(contract)}`")
        lines.append(f"   - **Outputs:** {_outputs_line(contract)}")
        if result.success:
            lines.append(f"   - **Path:** `{result.block_path}`")
            if result.test_result and result.test_result.summary_line:
                lines.append(f"   - **Tests:** {result.test_result.summary_line}")
        else:
            lines.append(f"   - **Error:** {result.message}")
        lines.append("")
        idx += 1

    if idx == 1:
        lines.append("_No blocks in this summary._")
        lines.append("")

    lines.extend(["### Execution flow", ""])

    if workflow_dag:
        # Simple arrow chain for PoC (linear or multi-edge as text)
        edges = [f"{a} → {b}" for a, b in workflow_dag]
        lines.append("```")
        lines.append("\n".join(edges))
        lines.append("```")
    else:
        lines.append("_No ordering edges were provided._")
    lines.append("")

    lines.extend(
        [
            "### Next steps",
            "",
            f"- Block directories live under `{blocks_root_display}<BlockName>/`.",
            "- Use the FaaSr Workflow Builder to wire actions and invoke workflows.",
            "",
        ]
    )

    return "\n".join(lines)
