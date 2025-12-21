from __future__ import annotations

import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def export_openapi_v1(*, output_path: Path) -> None:
    src_dir = _repo_root() / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from skriptoteket.web.app import create_app

    app = create_app()
    schema = app.openapi()

    paths = schema.get("paths", {})
    schema["paths"] = {path: item for path, item in paths.items() if path.startswith("/api/v1/")}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    output_path = _repo_root() / "frontend/apps/skriptoteket/openapi.json"
    export_openapi_v1(output_path=output_path)
    print(f"Wrote OpenAPI schema: {output_path}")


if __name__ == "__main__":
    main()
