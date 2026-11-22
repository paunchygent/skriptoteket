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
DEFAULT_RECORD_ROOT = Path(".artifacts/chat-edit-ops-context")


class _ScenarioPayload(TypedDict):
    tool_id: NotRequired[str | None]
    tool_slug: NotRequired[str | None]
    chat_message: NotRequired[str]
    edit_ops_message: NotRequired[str]
    active_file: NotRequired[str]


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


class _CaptureFile(TypedDict):
    payload: NotRequired[JsonValue]


class _CapturePayload(TypedDict):
    base_hash: NotRequired[JsonValue]
    base_hashes: NotRequired[JsonValue]
    virtual_files_source: NotRequired[JsonValue]
    omitted_virtual_file_ids: NotRequired[JsonValue]


_SCENARIO_PAYLOAD = TypeAdapter(_ScenarioPayload)
_EDITOR_BOOT = TypeAdapter(_EditorBootPayload)
_TOOL_LIST = TypeAdapter(list[_ToolRef])
_TOOLS_PAYLOAD = TypeAdapter(_ToolsPayload)
_CAPTURE_FILE = TypeAdapter(_CaptureFile)
_CAPTURE_PAYLOAD = TypeAdapter(_CapturePayload)


@dataclass(frozen=True)
class Scenario:
    tool_id: str | None
    tool_slug: str | None
    chat_message: str
    edit_ops_message: str
    active_file: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, JsonValue]) -> "Scenario":
        data = _SCENARIO_PAYLOAD.validate_python(payload)
        return cls(
            tool_id=data.get("tool_id"),
            tool_slug=data.get("tool_slug"),
            chat_message=data.get("chat_message", ""),
            edit_ops_message=data.get("edit_ops_message", ""),
            active_file=data.get("active_file", "tool.py"),
        )


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, JsonValue]:
    data: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a top-level JSON object in {path}")
    return data


def _write_json(path: Path, payload: JsonValue) -> None:
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


def _resolve_record_dir(base: Path | None) -> Path:
    root = base or DEFAULT_RECORD_ROOT
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    record_dir = root / timestamp
    record_dir.mkdir(parents=True, exist_ok=True)
    return record_dir


def _load_capture_payload(path: Path) -> _CapturePayload | None:
    if not path.exists():
        return None
    data: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    payload = _CAPTURE_FILE.validate_python(data).get("payload")
    if payload is None:
        return None
    return _CAPTURE_PAYLOAD.validate_python(payload)


@dataclass(frozen=True)
class _CaptureSummary:
    found: bool
    base_hash: JsonValue
    payload: dict[str, JsonValue]


def _summarize_capture(path: Path, label: str) -> _CaptureSummary:
    payload = _load_capture_payload(path)
    if payload is None:
        return _CaptureSummary(
            found=False,
            base_hash=None,
            payload={"label": label, "found": False},
        )
    base_hash = payload.get("base_hash")
    return _CaptureSummary(
        found=True,
        base_hash=base_hash,
        payload={
            "label": label,
            "found": True,
            "base_hash": base_hash,
            "base_hashes": payload.get("base_hashes"),
            "virtual_files_source": payload.get("virtual_files_source"),
            "omitted_virtual_file_ids": payload.get("omitted_virtual_file_ids"),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe chat + edit-ops base hashes in a single run.",
    )
    parser.add_argument("--scenario", type=Path, required=True, help="Scenario JSON")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--record-dir", type=Path)
    args = parser.parse_args()

    scenario = Scenario.from_payload(_read_json(args.scenario))
    if not scenario.chat_message or not scenario.edit_ops_message:
        raise SystemExit("Scenario must include chat_message and edit_ops_message")

    env = _load_env(Path(".env"))
    email = env.get("BOOTSTRAP_SUPERUSER_EMAIL")
    if not email:
        raise SystemExit("BOOTSTRAP_SUPERUSER_EMAIL missing in .env")

    chat_correlation_id = str(uuid.uuid4())
    edit_ops_correlation_id = str(uuid.uuid4())

    output_record_dir = _resolve_record_dir(args.record_dir)

    timeout = httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0)
    auth = create_signed_huleedu_api_session(
        email=email,
        display_name="Chat Edit Ops Probe Teacher",
        role="superuser",
        jti=f"chat-edit-ops-context-{chat_correlation_id}",
    )
    client = httpx.Client(base_url=args.base_url, timeout=timeout, headers=auth.signed_headers)
    try:
        if scenario.tool_id is None:
            tools_payload = client.get(
                "/api/v1/admin/tools",
                headers={"X-Correlation-ID": chat_correlation_id},
            )
            tools_payload.raise_for_status()
            tools_body: JsonValue = tools_payload.json()
            tools = _TOOL_LIST.validate_python(
                _TOOLS_PAYLOAD.validate_python(tools_body).get("tools", [])
            )
            if not scenario.tool_slug:
                raise SystemExit("Provide tool_id or tool_slug")
            tool_id = _select_tool_id_by_slug(tools, scenario.tool_slug)
            if tool_id is None:
                raise SystemExit(f"Tool slug not found: {scenario.tool_slug}")
        else:
            tool_id = scenario.tool_id

        boot_headers = {
            "X-Correlation-ID": chat_correlation_id,
        }
        boot_payload = client.get(f"/api/v1/editor/tools/{tool_id}", headers=boot_headers)
        boot_payload.raise_for_status()
        boot_data: JsonValue = boot_payload.json()
        virtual_files = _build_virtual_files(_EDITOR_BOOT.validate_python(boot_data))

        chat_payload: dict[str, JsonValue] = {
            "message": scenario.chat_message,
            "active_file": scenario.active_file,
            "virtual_files": virtual_files,
        }

        chat_headers = {
            "X-Correlation-ID": chat_correlation_id,
            "Accept": "text/event-stream",
        }
        with client.stream(
            "POST",
            f"/api/v1/editor/tools/{tool_id}/chat",
            headers=chat_headers,
            json=chat_payload,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    break

        edit_ops_payload: dict[str, JsonValue] = {
            "tool_id": tool_id,
            "message": scenario.edit_ops_message,
            "active_file": scenario.active_file,
            "virtual_files": virtual_files,
        }
        edit_ops_headers = {
            "X-Correlation-ID": edit_ops_correlation_id,
        }
        try:
            edit_ops_response = client.post(
                "/api/v1/editor/edit-ops",
                headers=edit_ops_headers,
                json=edit_ops_payload,
            )
            edit_ops_response.raise_for_status()
        except httpx.ReadTimeout:
            edit_ops_response = None

        record: dict[str, JsonValue] = {
            "captured_at": _utc_now_iso(),
            "tool_id": tool_id,
            "chat_correlation_id": chat_correlation_id,
            "edit_ops_correlation_id": edit_ops_correlation_id,
            "chat_message": scenario.chat_message,
            "edit_ops_message": scenario.edit_ops_message,
            "active_file": scenario.active_file,
        }

        _write_json(output_record_dir / "meta.json", record)
        _write_json(output_record_dir / "virtual_files.json", virtual_files)
        _write_json(output_record_dir / "chat.request.json", chat_payload)
        _write_json(output_record_dir / "edit_ops.request.json", edit_ops_payload)
        if edit_ops_response is not None:
            edit_ops_data: JsonValue = edit_ops_response.json()
            _write_json(output_record_dir / "edit_ops.response.json", edit_ops_data)
        else:
            _write_json(output_record_dir / "edit_ops.response.json", {"error": "read_timeout"})

        chat_capture = (
            Path(".artifacts/llm-captures/chat_request_context")
            / chat_correlation_id
            / "capture.json"
        )
        edit_ops_capture = (
            Path(".artifacts/llm-captures/chat_ops_response")
            / edit_ops_correlation_id
            / "capture.json"
        )

        chat_summary = _summarize_capture(chat_capture, "chat")
        edit_ops_summary = _summarize_capture(edit_ops_capture, "edit_ops")
        summary: dict[str, JsonValue] = {
            "chat_capture": chat_summary.payload,
            "edit_ops_capture": edit_ops_summary.payload,
        }
        _write_json(output_record_dir / "capture_summary.json", summary)

        print(f"record_dir={output_record_dir}")
        print(f"chat_correlation_id={chat_correlation_id}")
        print(f"edit_ops_correlation_id={edit_ops_correlation_id}")
        if chat_summary.found and edit_ops_summary.found:
            print(f"base_hash_match={chat_summary.base_hash == edit_ops_summary.base_hash}")
        elif edit_ops_response is None:
            print("edit_ops_status=read_timeout")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
