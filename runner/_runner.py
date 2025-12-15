from __future__ import annotations

import json
import os
import sys
import traceback
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any


def _load_module_from_path(*, module_path: Path) -> object:
    spec = spec_from_file_location("tool_script", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load tool script (invalid spec)")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _safe_error_summary(*, error: BaseException) -> str:
    return f"Tool execution failed ({type(error).__name__})."


def _collect_artifacts(*, work_dir: Path, output_dir: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for file_path in output_dir.rglob("*"):
        if not file_path.is_file():
            continue
        relative_to_work = file_path.relative_to(work_dir).as_posix()
        artifacts.append({"path": relative_to_work, "bytes": file_path.stat().st_size})
    artifacts.sort(key=lambda a: a["path"])
    return artifacts


def main() -> int:
    work_dir = Path("/work")

    script_path = Path(os.getenv("SKRIPTOTEKET_SCRIPT_PATH", "/work/script.py"))
    entrypoint = os.getenv("SKRIPTOTEKET_ENTRYPOINT", "run_tool").strip()
    input_path = Path(os.getenv("SKRIPTOTEKET_INPUT_PATH", "/work/input"))
    output_dir = Path(os.getenv("SKRIPTOTEKET_OUTPUT_DIR", "/work/output"))
    result_path = Path(os.getenv("SKRIPTOTEKET_RESULT_PATH", "/work/result.json"))

    status = "failed"
    html_output = ""
    error_summary: str | None = None
    artifacts: list[dict[str, Any]] = []

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        module = _load_module_from_path(module_path=script_path)

        func = getattr(module, entrypoint, None)
        if func is None or not callable(func):
            raise RuntimeError(f"Entrypoint not found: {entrypoint}")

        result = func(str(input_path), str(output_dir))
        if not isinstance(result, str):
            raise TypeError("Entrypoint must return a str (HTML output)")

        html_output = result
        status = "succeeded"
        artifacts = _collect_artifacts(work_dir=work_dir, output_dir=output_dir)

    except BaseException as e:  # noqa: BLE001 - runner boundary; writes a safe result.json
        error_summary = _safe_error_summary(error=e)
        traceback.print_exc(file=sys.stderr)

    payload = {
        "contract_version": 1,
        "status": status,
        "html_output": html_output,
        "error_summary": error_summary,
        "artifacts": artifacts,
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

