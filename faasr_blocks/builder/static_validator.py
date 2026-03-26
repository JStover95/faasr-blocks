"""AST-level validation: implementation shape vs contract."""

from __future__ import annotations

import ast

from faasr_blocks.builder.block_context import BlockContext
from faasr_blocks.builder.models import ValidationResult

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
    """
    Extract a string representation of a type annotation AST node.

    Args:
        node: AST node representing a type annotation (Name, Constant, Subscript, Attribute).

    Returns:
        String form of the annotation (e.g., "str", "dict", "Optional[int]"), or None if unparseable.
    """
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
    """
    Extract the function name from a call's func node.

    Args:
        func: AST expr node (typically ast.Name or ast.Attribute).

    Returns:
        Function name string, or None if not a simple name/attribute.
    """
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _string_arg_value(node: ast.expr) -> str | None:
    """
    Extract a string literal value from an AST node.

    Args:
        node: AST expr node (typically ast.Constant with a str value).

    Returns:
        The string value if node is a string constant, None otherwise.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _collect_faasr_secret_literals(tree: ast.AST) -> set[str]:
    """
    Find all string literals passed to faasr_secret() calls in the AST.

    Args:
        tree: AST tree to search (typically a function body).

    Returns:
        Set of secret name strings found in faasr_secret("SECRET_NAME") calls.
    """
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
    """
    Count how many times faasr_put_file() is called in the AST.

    Args:
        tree: AST tree to search.

    Returns:
        Number of faasr_put_file call sites found.
    """
    count = 0
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _call_name(n.func) == "faasr_put_file":
            count += 1
    return count


def _has_faasr_return_call(tree: ast.AST) -> bool:
    """
    Check if faasr_return() is called anywhere in the AST.

    Args:
        tree: AST tree to search.

    Returns:
        True if at least one faasr_return call is found, False otherwise.
    """
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _call_name(n.func) == "faasr_return":
            return True
    return False


def _returns_in_function_body(stmts: list[ast.stmt]) -> list[ast.Return]:
    """
    Collect ast.Return nodes under the contract entrypoint's statement list.

    Recurses through compound statements (if, loops, try, match, etc.) but does not descend into
    nested function or class definitions, since Python returns there are not the entrypoint's return.

    Args:
        stmts: Top-level statements of the contract function body.

    Returns:
        All return statements found in that scope.
    """
    found: list[ast.Return] = []
    for s in stmts:
        found.extend(_returns_in_stmt(s))
    return found


def _returns_in_stmt(stmt: ast.stmt) -> list[ast.Return]:
    """
    Collect ast.Return nodes reachable from a single statement, respecting scope boundaries.

    Args:
        stmt: One statement from the entrypoint body.

    Returns:
        Return nodes in this statement's nested suites; empty if none or if nested defs are skipped.
    """
    # Explicit return in the entrypoint body (forbidden for FaaSr).
    if isinstance(stmt, ast.Return):
        return [stmt]
    # Do not treat returns inside nested callables/classes as the entrypoint returning.
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return []
    # Branching and loops: search both suites (while/for orelse is else clause).
    if isinstance(stmt, ast.If):
        return _returns_in_function_body(stmt.body) + _returns_in_function_body(stmt.orelse)
    if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
        return _returns_in_function_body(stmt.body) + _returns_in_function_body(stmt.orelse)
    if isinstance(stmt, (ast.With, ast.AsyncWith)):
        return _returns_in_function_body(stmt.body)
    # try/except/finally/else: returns may appear in any arm.
    if isinstance(stmt, ast.Try):
        r = (
            _returns_in_function_body(stmt.body)
            + _returns_in_function_body(stmt.orelse)
            + _returns_in_function_body(stmt.finalbody)
        )
        for h in stmt.handlers:
            r.extend(_returns_in_function_body(h.body))
        return r
    # Pattern match: each case body is its own suite.
    if isinstance(stmt, ast.Match):
        r: list[ast.Return] = []
        for case in stmt.cases:
            r.extend(_returns_in_function_body(case.body))
        return r
    # PEP 654 try* (except*): same idea as Try for nested returns.
    try_star = getattr(ast, "TryStar", None)
    if try_star is not None and isinstance(stmt, try_star):
        r = (
            _returns_in_function_body(stmt.body)
            + _returns_in_function_body(stmt.orelse)
            + _returns_in_function_body(stmt.finalbody)
        )
        for h in stmt.handlers:
            r.extend(_returns_in_function_body(h.body))
        return r
    # Statements with no nested suites (assign, expr, import, etc.) cannot contain return.
    return []


def _is_faasr_return_expr_stmt(stmt: ast.stmt) -> bool:
    """
    Return True if stmt is a standalone expression statement calling faasr_return(...).

    Args:
        stmt: A statement from the function body.

    Returns:
        True exactly for `faasr_return(...)` used as a statement (not assigned or passed).
    """
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Call)
        and _call_name(stmt.value.func) == "faasr_return"
    )


def _if_branches_all_end_with_faasr_return(if_node: ast.If) -> bool:
    """
    Return True if both if-body and else-branch end every path with faasr_return.

    An if without else cannot satisfy this: the false branch falls through past the if.

    Args:
        if_node: An if statement in the entrypoint body.

    Returns:
        True if if and else suites each satisfy _block_all_paths_end_with_faasr_return.
    """
    # Without else, the condition-false path continues after the if — not all paths end in faasr_return here.
    if not if_node.orelse:
        return False
    return _block_all_paths_end_with_faasr_return(
        if_node.body
    ) and _block_all_paths_end_with_faasr_return(if_node.orelse)


def _stmt_ends_all_paths_with_faasr_return(stmt: ast.stmt) -> bool:
    """
    Return True if every execution path through this single statement ends with faasr_return.

    Covers a lone faasr_return call, if/else where both branches qualify, and match where every
    case body qualifies. Other shapes (try, loops, bare if) are treated as not satisfying.

    Args:
        stmt: One statement, typically the last in a block or under analysis.

    Returns:
        True if no path can complete this statement without faasr_return as the last executed line.
    """
    # Single statement that is exactly faasr_return(...).
    if _is_faasr_return_expr_stmt(stmt):
        return True
    if isinstance(stmt, ast.If):
        return _if_branches_all_end_with_faasr_return(stmt)
    if isinstance(stmt, ast.Match):
        # No cases means no path can end in faasr_return inside the match.
        if not stmt.cases:
            return False
        return all(_block_all_paths_end_with_faasr_return(c.body) for c in stmt.cases)
    return False


def _stmt_always_raises(stmt: ast.stmt) -> bool:
    """
    Return True if this statement always raises (never falls through normally).

    Args:
        stmt: One statement.

    Returns:
        True for a bare raise statement only (approximation; no constant folding).
    """
    return isinstance(stmt, ast.Raise)


def _stmt_may_fall_through_to_next(stmt: ast.stmt) -> bool:
    """
    Return True if execution can reach the next sibling statement in the same block.

    faasr_return and raise do not fall through. if without else always allows the false branch
    to continue after the if. if/else where both branches end in faasr_return does not fall through.

    Args:
        stmt: One statement before a possible successor in the same list.

    Returns:
        True when a successor may run; False when this stmt always exits the block first.
    """
    # faasr_return ends the function from FaaSr's perspective; nothing runs after on that path.
    if _is_faasr_return_expr_stmt(stmt):
        return False
    if _stmt_always_raises(stmt):
        return False
    if isinstance(stmt, ast.If):
        # No else: when the test is false, control skips the body and runs the next stmt.
        if not stmt.orelse:
            return True
        # Both branches end in faasr_return: no path reaches the stmt after this if.
        return not _if_branches_all_end_with_faasr_return(stmt)
    if isinstance(stmt, ast.Match):
        # If every case ends with faasr_return, control never reaches the following stmt.
        return not _stmt_ends_all_paths_with_faasr_return(stmt)
    return True


def _block_all_paths_end_with_faasr_return(stmts: list[ast.stmt]) -> bool:
    """
    Return True if every execution path through this statement list ends with faasr_return(...).

    For a non-empty list, either an early statement exits every path via faasr_return (later stmts
    unreachable) or each non-final statement must fall through, and the final statement must end
    all paths with faasr_return. Empty body fails.

    Args:
        stmts: A linear sequence of statements (e.g. function body or if-branch).

    Returns:
        True if there is no fall-through off the end of the list without faasr_return as last line.
    """
    # Empty suite: nothing calls faasr_return, so bool contract is not satisfied.
    if not stmts:
        return False
    for stmt in stmts[:-1]:
        # All paths through this stmt end with faasr_return; remaining stmts are dead — still valid.
        if _stmt_ends_all_paths_with_faasr_return(stmt):
            return True
        # Stmt never reaches the next line (e.g. stuck loop): cannot prove bool contract for whole block.
        if not _stmt_may_fall_through_to_next(stmt):
            # All paths that reach this stmt raise: no normal completion; treat as satisfied for this prefix.
            if _stmt_always_raises(stmt):
                return True
            return False
    # Final statement must end every path with faasr_return (or qualifying if/match).
    return _stmt_ends_all_paths_with_faasr_return(stmts[-1])


class StaticValidator:
    """
    Validate that a Python source file's implementation structurally matches a contract.

    This validator performs AST-level checks without executing code:
    - Function name and parameter list match the contract
    - Required secrets appear in faasr_secret() calls as string literals
    - At least one faasr_put_file() call exists when S3 outputs are declared
    - bool contracts: every path ends with faasr_return(...) as the last executed statement
    - No Python return in the entrypoint; return annotations should not imply a bool return value
    - Type hints match contract types (warnings only, not errors)
    """

    def __init__(self, context: BlockContext) -> None:
        self._context = context

    def validate(self) -> ValidationResult:
        """
        Parse the block's source file and check it implements the contract's function specification.

        Returns:
            ValidationResult with ok=True if all checks pass, or ok=False with detailed errors.
        """
        # Pull context values
        contract = self._context.contract
        source_file = self._context.src_file
        function_name = self._context.function_name

        errors: list[str] = []
        warnings: list[str] = []

        # Validate that the file exists and is a valid Python file
        # Missing src file: cannot run any AST checks.
        if not source_file.is_file():
            return ValidationResult.failure([f"Source file not found: {source_file}"])
        try:
            src = source_file.read_text(encoding="utf-8")
            tree = ast.parse(src, filename=str(source_file))
        # Unparseable Python: fail fast with the compiler error.
        except SyntaxError as e:
            return ValidationResult.failure([f"Syntax error: {e}"])
        # I/O failure reading the module (permissions, etc.).
        except OSError as e:
            return ValidationResult.failure([f"Failed to read source: {e}"])

        # Validate that a matching module-level function exists and is not async
        func_node: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        for node in tree.body:
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == function_name
            ):
                func_node = node
                break
        # No matching def: contract names an entrypoint that is not defined at module level.
        if func_node is None:
            errors.append(f"No top-level function definition named {function_name!r}")
            return ValidationResult.failure(errors)
        if isinstance(func_node, ast.AsyncFunctionDef):
            errors.append(f"Function {function_name} must not be async for FaaSr blocks")

        # Validate that all function parameters match the contract
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

        body_tree = ast.Module(body=func_node.body, type_ignores=[])

        # Validate that the entrypoint does not use a Python `return`
        if _returns_in_function_body(func_node.body):
            errors.append(
                "FaaSr block entrypoint must not use a Python `return`; "
                "use faasr_return(...) only when contract return_type is bool, "
                "otherwise fall through without returning a value"
            )

        # Append warnings for misleading return annotations (bool or other types)
        ret_ann = _annotation_string(func_node.returns)
        if ret_ann is not None and ret_ann != "None":
            if ret_ann == "bool":
                warnings.append(
                    "Return annotation `bool` is misleading: the entrypoint returns no Python value; "
                    "express bool semantics with faasr_return(...) when return_type is bool"
                )
            else:
                warnings.append(
                    f"Return annotation is {ret_ann!r}; FaaSr entrypoints should annotate None or omit it"
                )

        # Validate that every path ends with faasr_return as the last executed line when the contract return_type is bool
        if contract.function.return_type == "bool":
            if not _block_all_paths_end_with_faasr_return(func_node.body):
                errors.append(
                    "Contract return_type is bool: every execution path must end with faasr_return(...) "
                    "as the last executed statement (no Python `return`, and no fall-through past the call)"
                )

        # Validate that faasr_return is not called when the contract return_type is not bool
        elif _has_faasr_return_call(body_tree):
            errors.append(
                "faasr_return() is only allowed when contract function return_type is bool"
            )

        # Validate that all function argument type hints match the contract
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

        # Validate that all required secrets are passed to faasr_secret() as string literals
        secrets_used = _collect_faasr_secret_literals(body_tree)
        for sec in contract.required_secrets:
            if sec not in secrets_used:
                errors.append(
                    f"Required secret {sec!r} not passed to faasr_secret() as a string literal in {function_name}"
                )

        # Validate that at least one faasr_put_file is called when S3 outputs are declared
        if contract.s3_outputs:
            n_put = _count_faasr_put_file_calls(body_tree)
            if n_put < 1:
                errors.append(
                    "Contract declares s3_outputs but function body has no faasr_put_file() calls"
                )

        # If any errors were recorded, return a failure result.
        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult(ok=True, errors=[], warnings=warnings)
