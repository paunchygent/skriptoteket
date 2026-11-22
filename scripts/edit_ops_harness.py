from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import NotRequired, TypedDict

import httpx
from pydantic import JsonValue, TypeAdapter

from scripts._playwright_huleedu_auth import create_signed_huleedu_api_session

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_SCENARIO_DIR = Path("scripts/edit_ops_scenarios")
DEFAULT_RECORD_ROOT = Path(".artifacts/edit-ops-harness")


class _ScenarioPayload(TypedDict):
    tool_id: NotRequired[str | None]
    tool_slug: NotRequired[str | None]
    message: NotRequired[str | None]
    active_file: NotRequired[str]
    selection: NotRequired[dict[str, JsonValue] | None]
    cursor: NotRequired[dict[str, JsonValue] | None]
    ops: NotRequired[list[JsonValue] | None]


class _EditorBootPayload(TypedDict):
    source_code: NotRequired[str | None]
    entrypoint: NotRequired[str | None]
    settings_schema: NotRequired[JsonValue]
    input_schema: NotRequired[JsonValue]
    usage_instructions: NotRequired[str | None]


class _ToolRef(TypedDict):
    slug: NotRequired[str]
    id: NotRequired[str]


class _ToolsPayload(TypedDict):
    tools: NotRequired[JsonValue]


class _EditOpsResponse(TypedDict):
    ops: NotRequired[JsonValue]


class _OkResult(TypedDict):
    ok: NotRequired[bool]


class _PreviewMeta(TypedDict):
    base_hash: NotRequired[str]
    patch_id: NotRequired[str]


class _PreviewResult(_OkResult):
    meta: NotRequired[_PreviewMeta]


_SCENARIO_PAYLOAD = TypeAdapter(_ScenarioPayload)
_EDITOR_BOOT = TypeAdapter(_EditorBootPayload)
_TOOL_LIST = TypeAdapter(list[_ToolRef])
_TOOLS_PAYLOAD = TypeAdapter(_ToolsPayload)
_EDIT_OPS_RESPONSE = TypeAdapter(_EditOpsResponse)
_PREVIEW_RESULT = TypeAdapter(_PreviewResult)
_APPLY_RESULT = TypeAdapter(_OkResult)


def _expect_object(value: JsonValue, *, context: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object for {context}, got {type(value).__name__}")
    return value


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, JsonValue]:
    data: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a top-level JSON object in {path}")
    return data


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        raise SystemExit(".env not found; create from .env.example")
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _stringify_schema(schema: JsonValue) -> str:
    if schema is None:
        return ""
    return json.dumps(schema, ensure_ascii=False, indent=2)


def _build_virtual_files(editor_boot: _EditorBootPayload) -> dict[str, JsonValue]:
    return {
        "tool.py": editor_boot.get("source_code") or "",
        "entrypoint.txt": editor_boot.get("entrypoint") or "",
        "settings_schema.json": _stringify_schema(editor_boot.get("settings_schema")),
        "input_schema.json": _stringify_schema(editor_boot.get("input_schema")),
        "usage_instructions.md": editor_boot.get("usage_instructions") or "",
    }


def _select_tool_id_by_slug(tools: Sequence[_ToolRef], slug: str) -> str | None:
    for tool in tools:
        if tool.get("slug") == slug:
            return str(tool.get("id"))
    return None


@dataclass(frozen=True)
class Scenario:
    tool_id: str | None
    tool_slug: str | None
    message: str | None
    active_file: str
    selection: dict[str, JsonValue] | None
    cursor: dict[str, JsonValue] | None
    ops: list[JsonValue] | None

    @classmethod
    def from_payload(cls, payload: Mapping[str, JsonValue]) -> "Scenario":
        data = _SCENARIO_PAYLOAD.validate_python(payload)
        return cls(
            tool_id=data.get("tool_id"),
            tool_slug=data.get("tool_slug"),
            message=data.get("message"),
            active_file=data.get("active_file", "tool.py"),
            selection=data.get("selection"),
            cursor=data.get("cursor"),
            ops=data.get("ops"),
        )


class HarnessClient:
    def __init__(self, *, base_url: str, email: str, correlation_id: str) -> None:
        auth = create_signed_huleedu_api_session(
            email=email,
            display_name="Edit Ops Harness Teacher",
            role="superuser",
            jti=f"edit-ops-harness-{correlation_id}",
        )
        self._client = httpx.Client(
            base_url=base_url,
            timeout=60.0,
            headers=auth.signed_headers,
        )

    def close(self) -> None:
        self._client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, JsonValue] | None,
        correlation_id: str,
    ) -> dict[str, JsonValue]:
        headers = {
            "X-Correlation-ID": correlation_id,
        }
        response = self._client.request(method, path, json=payload, headers=headers)
        response.raise_for_status()
        data: JsonValue = response.json()
        return _expect_object(data, context=f"{method} {path}")

    def get(self, path: str, *, correlation_id: str) -> dict[str, JsonValue]:
        headers = {
            "X-Correlation-ID": correlation_id,
        }
        response = self._client.get(path, headers=headers)
        response.raise_for_status()
        data: JsonValue = response.json()
        return _expect_object(data, context=f"GET {path}")


def _load_scenario(path: Path) -> Scenario:
    payload = _read_json(path)
    return Scenario.from_payload(payload)


def _resolve_record_dir(base: Path | None) -> Path:
    root = base or DEFAULT_RECORD_ROOT
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    record_dir = root / timestamp
    record_dir.mkdir(parents=True, exist_ok=True)
    return record_dir


def _mode_choices() -> list[str]:
    return ["generate", "preview", "apply", "full"]


def _print_result(label: str, payload: _OkResult) -> None:
    print(f"{label}: ok={payload.get('ok', 'n/a')}")


def _run_preview_apply(
    client: HarnessClient,
    *,
    preview_request: dict[str, JsonValue],
    mode: str,
    correlation_id: str,
    output_record_dir: Path | None,
) -> bool:
    """Run preview (and apply in apply/full mode); return False when a step is not ok.

    The recorded response files hold the full parsed HTTP response; the typed
    views only drive control flow.
    """
    preview_raw = client.request(
        "POST",
        "/api/v1/editor/edit-ops/preview",
        payload=preview_request,
        correlation_id=correlation_id,
    )
    preview_response = _PREVIEW_RESULT.validate_python(preview_raw)
    if output_record_dir:
        _write_json(output_record_dir / "preview.request.json", preview_request)
        _write_json(output_record_dir / "preview.response.json", preview_raw)

    _print_result("preview", preview_response)
    if not preview_response.get("ok"):
        return False

    if mode in {"apply", "full"}:
        meta = preview_response.get("meta", _PreviewMeta())
        apply_request = dict(preview_request)
        apply_request["base_hash"] = meta.get("base_hash")
        apply_request["patch_id"] = meta.get("patch_id")

        apply_raw = client.request(
            "POST",
            "/api/v1/editor/edit-ops/apply",
            payload=apply_request,
            correlation_id=correlation_id,
        )
        apply_response = _APPLY_RESULT.validate_python(apply_raw)
        if output_record_dir:
            _write_json(output_record_dir / "apply.request.json", apply_request)
            _write_json(output_record_dir / "apply.response.json", apply_raw)

        _print_result("apply", apply_response)
        if not apply_response.get("ok"):
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Edit-ops harness (generate/preview/apply).")
    parser.add_argument(
        "--scenario",
        type=Path,
        help="Path to scenario JSON (default: scripts/edit_ops_scenarios/<name>.json)",
    )
    parser.add_argument(
        "--scenario-name",
        help="Scenario file name inside scripts/edit_ops_scenarios",
    )
    parser.add_argument("--mode", choices=_mode_choices(), default="full")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--record", action="store_true", help="Record requests/responses")
    parser.add_argument("--record-dir", type=Path, help="Override record directory root")
    parser.add_argument("--replay", type=Path, help="Replay from a recorded bundle")
    parser.add_argument("--correlation-id", help="Override correlation ID")
    parser.add_argument("--tool-id", help="Override tool ID from scenario")
    parser.add_argument("--tool-slug", help="Override tool slug from scenario")
    parser.add_argument("--apply", action="store_true", help="Alias to set mode=apply")

    args = parser.parse_args()

    if args.apply:
        args.mode = "apply"

    if args.replay and args.mode == "generate":
        raise SystemExit("Replay mode does not support generate-only. Use preview/apply/full.")

    correlation_id = args.correlation_id or str(uuid.uuid4())

    output_record_dir: Path | None = None
    if args.record:
        output_record_dir = _resolve_record_dir(args.record_dir)

    if args.replay:
        return _run_replay(
            replay_dir=args.replay,
            mode=args.mode,
            base_url=args.base_url,
            correlation_id=correlation_id,
            output_record_dir=output_record_dir,
        )

    scenario_path = args.scenario
    if scenario_path is None and args.scenario_name:
        scenario_path = DEFAULT_SCENARIO_DIR / args.scenario_name
    if scenario_path is None:
        raise SystemExit("Provide --scenario or --scenario-name")
    scenario = _load_scenario(scenario_path)

    tool_id = args.tool_id or scenario.tool_id
    tool_slug = args.tool_slug or scenario.tool_slug

    env = _load_env(Path(".env"))
    email = env.get("BOOTSTRAP_SUPERUSER_EMAIL")
    if not email:
        raise SystemExit("BOOTSTRAP_SUPERUSER_EMAIL missing in .env")

    client = HarnessClient(base_url=args.base_url, email=email, correlation_id=correlation_id)
    try:
        if tool_id is None:
            tools_payload = _TOOLS_PAYLOAD.validate_python(
                client.get("/api/v1/admin/tools", correlation_id=correlation_id)
            )
            tools = _TOOL_LIST.validate_python(tools_payload.get("tools", []))
            if not tool_slug:
                raise SystemExit("Provide tool_id or tool_slug (scenario or CLI).")
            tool_id = _select_tool_id_by_slug(tools, tool_slug)
            if tool_id is None:
                available = ", ".join(sorted(t.get("slug", "") for t in tools))
                raise SystemExit(f"Tool slug not found: {tool_slug}. Available: {available}")

        boot_payload = _EDITOR_BOOT.validate_python(
            client.get(f"/api/v1/editor/tools/{tool_id}", correlation_id=correlation_id)
        )
        virtual_files = _build_virtual_files(boot_payload)

        if output_record_dir:
            _write_json(
                output_record_dir / "scenario.json",
                {
                    "tool_id": tool_id,
                    "tool_slug": tool_slug,
                    "message": scenario.message,
                    "active_file": scenario.active_file,
                    "selection": scenario.selection,
                    "cursor": scenario.cursor,
                    "ops": scenario.ops,
                },
            )
            _write_json(output_record_dir / "virtual_files.json", virtual_files)

        ops: JsonValue = scenario.ops
        if args.mode in {"generate", "full"}:
            if not scenario.message:
                raise SystemExit("Scenario missing message for generate/full mode.")
            edit_ops_request: dict[str, JsonValue] = {
                "tool_id": tool_id,
                "message": scenario.message,
                "active_file": scenario.active_file,
                "virtual_files": virtual_files,
            }
            if scenario.selection:
                edit_ops_request["selection"] = scenario.selection
            if scenario.cursor:
                edit_ops_request["cursor"] = scenario.cursor

            edit_ops_raw = client.request(
                "POST",
                "/api/v1/editor/edit-ops",
                payload=edit_ops_request,
                correlation_id=correlation_id,
            )
            if output_record_dir:
                _write_json(output_record_dir / "edit_ops.request.json", edit_ops_request)
                _write_json(output_record_dir / "edit_ops.response.json", edit_ops_raw)

            ops = _EDIT_OPS_RESPONSE.validate_python(edit_ops_raw).get("ops")
            if not ops:
                raise SystemExit("Edit-ops response contained no ops.")

        if args.mode in {"preview", "apply", "full"}:
            if not ops:
                raise SystemExit("No ops provided for preview/apply.")

            preview_request: dict[str, JsonValue] = {
                "tool_id": tool_id,
                "active_file": scenario.active_file,
                "virtual_files": virtual_files,
                "ops": ops,
            }
            if scenario.selection:
                preview_request["selection"] = scenario.selection
            if scenario.cursor:
                preview_request["cursor"] = scenario.cursor

            if not _run_preview_apply(
                client,
                preview_request=preview_request,
                mode=args.mode,
                correlation_id=correlation_id,
                output_record_dir=output_record_dir,
            ):
                return 1

        if output_record_dir:
            _write_json(
                output_record_dir / "meta.json",
                {
                    "captured_at": _utc_now_iso(),
                    "mode": args.mode,
                    "base_url": args.base_url,
                    "tool_id": tool_id,
                    "tool_slug": tool_slug,
                    "correlation_id": correlation_id,
                },
            )

        print(f"correlation_id={correlation_id}")
        if output_record_dir:
            print(f"record_dir={output_record_dir}")
        return 0
    finally:
        client.close()


def _run_replay(
    *,
    replay_dir: Path,
    mode: str,
    base_url: str,
    correlation_id: str,
    output_record_dir: Path | None,
) -> int:
    if not replay_dir.exists():
        raise SystemExit(f"Replay directory not found: {replay_dir}")

    preview_request_path = replay_dir / "preview.request.json"
    if not preview_request_path.exists():
        raise SystemExit("Replay bundle missing preview.request.json")

    preview_request = _read_json(preview_request_path)

    env = _load_env(Path(".env"))
    email = env.get("BOOTSTRAP_SUPERUSER_EMAIL")
    if not email:
        raise SystemExit("BOOTSTRAP_SUPERUSER_EMAIL missing in .env")

    client = HarnessClient(base_url=base_url, email=email, correlation_id=correlation_id)
    try:
        if not _run_preview_apply(
            client,
            preview_request=preview_request,
            mode=mode,
            correlation_id=correlation_id,
            output_record_dir=output_record_dir,
        ):
            return 1

        if output_record_dir:
            _write_json(
                output_record_dir / "meta.json",
                {
                    "captured_at": _utc_now_iso(),
                    "mode": mode,
                    "base_url": base_url,
                    "correlation_id": correlation_id,
                    "replay_of": str(replay_dir),
                },
            )

        print(f"correlation_id={correlation_id}")
        if output_record_dir:
            print(f"record_dir={output_record_dir}")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
