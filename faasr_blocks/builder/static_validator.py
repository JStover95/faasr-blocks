"""AST-level validation: implementation shape vs contract."""

from __future__ import annotations

import ast
from pathlib import Path

from faasr_blocks.builder.models import ValidationResult
from faasr_blocks.models.contract import Contract

# Map contract argument types to acceptable ast annotation nodes (by string form).
_TYPE_ALIASES: dict[str, set[str]] = {
    "str": {"str"},
    "int": {"int"},
    "float": {"float"},
    "bool": {"bool"},
    "dict": {"dict"},
    "list": {"list"},
    "Any": {"Any"},
}


def _annotation_string(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Subscript):
        base = _annotation_string(node.value)
        if base:
            return f"{base}[...]"
        return None
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        cur: ast.expr = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
    return None


def _call_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _string_arg_value(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _collect_faasr_secret_literals(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        name = _call_name(n.func)
        if name != "faasr_secret":
            continue
        if n.args:
            s = _string_arg_value(n.args[0])
            if s is not None:
                found.add(s)
        for kw in n.keywords:
            if kw.arg == "secret_name" or kw.arg is None:
                s = _string_arg_value(kw.value)
                if s is not None:
                    found.add(s)
    return found


def _count_faasr_put_file_calls(tree: ast.AST) -> int:
    count = 0
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _call_name(n.func) == "faasr_put_file":
            count += 1
    return count


def _has_faasr_return_call(tree: ast.AST) -> bool:
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _call_name(n.func) == "faasr_return":
            return True
    return False


class StaticValidator:
    """Validate that ``source_file`` defines a function matching ``contract``."""

    def validate(self, contract: Contract, source_file: Path) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not source_file.is_file():
            return ValidationResult.failure([f"Source file not found: {source_file}"])

        try:
            src = source_file.read_text(encoding="utf-8")
            tree = ast.parse(src, filename=str(source_file))
        except SyntaxError as e:
            return ValidationResult.failure([f"Syntax error: {e}"])
        except OSError as e:
            return ValidationResult.failure([f"Failed to read source: {e}"])

        fn_name = contract.function.name
        func_node: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
                func_node = node
                break

        if func_node is None:
            errors.append(f"No top-level function definition named {fn_name!r}")
            return ValidationResult.failure(errors)

        if isinstance(func_node, ast.AsyncFunctionDef):
            errors.append(f"Function {fn_name} must not be async for FaaSr blocks")

        # Parameters (no *args / **kwargs for strict PoC match)
        expected_args = list(contract.function.arguments.keys())
        posonly = list(func_node.args.posonlyargs)
        args = list(func_node.args.args)
        kwonly = list(func_node.args.kwonlyargs)
        if func_node.args.vararg is not None or func_node.args.kwarg is not None:
            errors.append("Function must not use *args or **kwargs for contract compliance")

        all_params = [a.arg for a in posonly + args + kwonly]
        if all_params != expected_args:
            errors.append(
                f"Parameter list mismatch: expected {expected_args!r}, got {all_params!r}"
            )

        # Return annotation
        ret_ann = _annotation_string(func_node.returns)
        if contract.function.return_type == "bool":
            if ret_ann not in ("bool", None):
                warnings.append(
                    f"Return annotation is {ret_ann!r}; contract expects bool (optional hint)"
                )
            if not _has_faasr_return_call(func_node):
                errors.append(
                    "Contract return_type is bool but no faasr_return() call found in function body"
                )
        else:
            if ret_ann not in ("None", None):
                warnings.append(
                    f"Return annotation is {ret_ann!r}; contract expects None (optional hint)"
                )

        # Argument type hints vs contract
        arg_map = {a.arg: a for a in posonly + args + kwonly}
        for name, spec in contract.function.arguments.items():
            if name not in arg_map:
                continue
            ann = _annotation_string(arg_map[name].annotation)
            if ann is None:
                continue
            allowed = _TYPE_ALIASES.get(spec.type, {spec.type})
            if ann not in allowed and ann != spec.type:
                warnings.append(
                    f"Argument {name!r} annotation {ann!r} may not match contract type {spec.type!r}"
                )

        # Secrets
        body_tree = ast.Module(body=func_node.body, type_ignores=[])
        secrets_used = _collect_faasr_secret_literals(body_tree)
        for sec in contract.required_secrets:
            if sec not in secrets_used:
                errors.append(
                    f"Required secret {sec!r} not passed to faasr_secret() as a string literal in {fn_name}"
                )

        # S3 outputs: require at least one faasr_put_file when outputs declared
        if contract.s3_outputs:
            n_put = _count_faasr_put_file_calls(body_tree)
            if n_put < 1:
                errors.append(
                    "Contract declares s3_outputs but function body has no faasr_put_file() calls"
                )

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult(ok=True, errors=[], warnings=warnings)
