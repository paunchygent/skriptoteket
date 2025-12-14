from __future__ import annotations

import ast
from pathlib import Path

import pytest

_RULE_REF = ".agent/rules/040-fastapi-blueprint.md (OpenAPI-safe typing)"
_ROUTE_MODULE_DIRS = (
    "src/skriptoteket/web/pages",
    "src/skriptoteket/web/partials",
    "src/skriptoteket/api",
)
_RESPONSE_TYPE_NAMES = frozenset(
    {
        "FileResponse",
        "HTMLResponse",
        "JSONResponse",
        "PlainTextResponse",
        "RedirectResponse",
        "Response",
        "StreamingResponse",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iter_route_module_paths(*, root: Path) -> list[Path]:
    paths: list[Path] = []
    for rel_dir in _ROUTE_MODULE_DIRS:
        module_dir = root / rel_dir
        if not module_dir.exists():
            continue
        paths.extend(path for path in module_dir.rglob("*.py") if path.is_file())
    return sorted(set(paths))


def _has_future_annotations_import(module: ast.Module) -> bool:
    for node in module.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            if any(alias.name == "annotations" for alias in node.names):
                return True
    return False


def _flatten_bit_or_union(node: ast.AST) -> list[ast.AST] | None:
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.BitOr):
        return None
    return _flatten_union_operands(node)


def _flatten_union_operands(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _flatten_union_operands(node.left) + _flatten_union_operands(node.right)
    return [node]


def _contains_response_type(node: ast.AST) -> bool:
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Name) and subnode.id in _RESPONSE_TYPE_NAMES:
            return True
        if isinstance(subnode, ast.Attribute) and subnode.attr in _RESPONSE_TYPE_NAMES:
            return True
    return False


def test_route_modules_follow_openapi_safe_typing_rules() -> None:
    root = _repo_root()
    future_import_violations: list[str] = []
    response_union_violations: list[str] = []

    for path in _iter_route_module_paths(root=root):
        rel = path.relative_to(root).as_posix()
        module = ast.parse(path.read_text(encoding="utf-8"), filename=rel)

        if _has_future_annotations_import(module):
            future_import_violations.append(rel)

        for node in ast.walk(module):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.returns is None:
                continue

            operands = _flatten_bit_or_union(node.returns)
            if not operands:
                continue

            if any(_contains_response_type(operand) for operand in operands):
                response_union_violations.append(f"{rel}:{node.name}")

    if not future_import_violations and not response_union_violations:
        return

    message_lines = [
        "OpenAPI-safe routing rules violated (these can break `/docs` and `/openapi.json`).",
        f"See {_RULE_REF}.",
    ]

    if future_import_violations:
        message_lines.extend(
            [
                "",
                "FORBIDDEN: `from __future__ import annotations` found in route modules:",
                *[f"- {p}" for p in future_import_violations],
            ]
        )

    if response_union_violations:
        message_lines.extend(
            [
                "",
                "FORBIDDEN: Union return type hints involving Starlette/FastAPI response types:",
                *[f"- {p}" for p in response_union_violations],
            ]
        )

    raise AssertionError("\n".join(message_lines))


def test_openapi_schema_builds() -> None:
    from skriptoteket.web.app import create_app

    app = create_app()
    try:
        schema = app.openapi()
    except Exception as exc:  # noqa: BLE001
        pytest.fail(
            "\n".join(
                [
                    f"OpenAPI schema generation failed: {exc!r}",
                    "This commonly indicates an OpenAPI-unsafe route signature/type hint.",
                    f"See {_RULE_REF}.",
                ]
            )
        )

    assert schema.get("info", {}).get("title")
