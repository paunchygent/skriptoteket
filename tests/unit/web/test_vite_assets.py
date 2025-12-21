from __future__ import annotations

import json
from pathlib import Path

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.web.vite import ViteAssets


@pytest.mark.unit
def test_vite_tags_dev_server_renders_vite_client_and_entrypoint() -> None:
    vite = ViteAssets(
        dev_server_url="http://localhost:5173/",
        manifest_path=Path("/does-not-matter.json"),
        static_base_url="/static/spa",
    )

    rendered = str(vite.tags("src/entrypoints/demo.ts"))
    assert 'src="http://localhost:5173/@vite/client"' in rendered
    assert 'src="http://localhost:5173/src/entrypoints/demo.ts"' in rendered


@pytest.mark.unit
def test_vite_tags_manifest_renders_css_preload_and_entry_script(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "src/entrypoints/demo.ts": {
                    "file": "assets/demo-abc123.js",
                    "imports": ["assets/vendor-xyz999.js"],
                    "css": ["assets/demo-abc123.css"],
                },
                "assets/vendor-xyz999.js": {
                    "file": "assets/vendor-xyz999.js",
                    "css": ["assets/vendor-xyz999.css"],
                },
            }
        ),
        encoding="utf-8",
    )

    vite = ViteAssets(
        dev_server_url=None,
        manifest_path=manifest_path,
        static_base_url="/static/spa",
    )

    rendered = str(vite.tags("src/entrypoints/demo.ts"))
    assert 'rel="stylesheet" href="/static/spa/assets/demo-abc123.css"' in rendered
    assert 'rel="stylesheet" href="/static/spa/assets/vendor-xyz999.css"' in rendered
    assert 'rel="modulepreload" href="/static/spa/assets/vendor-xyz999.js"' in rendered
    assert 'type="module" src="/static/spa/assets/demo-abc123.js"' in rendered


@pytest.mark.unit
def test_vite_tags_manifest_missing_entrypoint_raises_domain_error(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({}), encoding="utf-8")

    vite = ViteAssets(
        dev_server_url=None,
        manifest_path=manifest_path,
        static_base_url="/static/spa",
    )

    with pytest.raises(DomainError) as excinfo:
        vite.tags("src/entrypoints/missing.ts")

    assert excinfo.value.code == ErrorCode.INTERNAL_ERROR
