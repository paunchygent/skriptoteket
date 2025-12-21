from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

from markupsafe import Markup, escape

from skriptoteket.domain.errors import DomainError, ErrorCode


class _ManifestEntry(TypedDict, total=False):
    file: str
    css: list[str]
    imports: list[str]


type _Manifest = dict[str, _ManifestEntry]


class ViteAssets:
    def __init__(
        self,
        *,
        dev_server_url: str | None,
        manifest_path: Path,
        static_base_url: str,
    ) -> None:
        self._dev_server_url = dev_server_url.rstrip("/") if dev_server_url else None
        self._manifest_path = manifest_path
        self._static_base_url = static_base_url.rstrip("/") + "/"
        self._cached_manifest_mtime: float | None = None
        self._cached_manifest: _Manifest | None = None

    def tags(self, entrypoint: str) -> Markup:
        if self._dev_server_url:
            return Markup(
                "\n".join(
                    [
                        self._script_tag(f"{self._dev_server_url}/@vite/client"),
                        self._script_tag(f"{self._dev_server_url}/{entrypoint.lstrip('/')}"),
                    ]
                )
            )

        manifest = self._load_manifest()
        if entrypoint not in manifest:
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Vite manifest missing entrypoint.",
                details={
                    "entrypoint": entrypoint,
                    "manifest_path": str(self._manifest_path),
                },
            )

        css_files = self._collect_css(manifest, entrypoint)
        preload_files = self._collect_modulepreload_files(manifest, entrypoint)
        entry_file = manifest[entrypoint].get("file")
        if not entry_file:
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Vite manifest entrypoint is missing file.",
                details={
                    "entrypoint": entrypoint,
                    "manifest_path": str(self._manifest_path),
                },
            )

        tags: list[str] = []
        for css_file in css_files:
            tags.append(self._css_tag(self._static_url(css_file)))
        for preload_file in preload_files:
            tags.append(self._modulepreload_tag(self._static_url(preload_file)))
        tags.append(self._script_tag(self._static_url(entry_file)))

        return Markup("\n".join(tags))

    def _load_manifest(self) -> _Manifest:
        try:
            mtime = self._manifest_path.stat().st_mtime
        except FileNotFoundError as exc:
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Vite manifest not found. Run pnpm build or configure VITE_DEV_SERVER_URL.",
                details={"manifest_path": str(self._manifest_path)},
            ) from exc

        if self._cached_manifest is not None and self._cached_manifest_mtime == mtime:
            return self._cached_manifest

        raw = self._manifest_path.read_text(encoding="utf-8")
        manifest = cast(_Manifest, json.loads(raw))
        self._cached_manifest = manifest
        self._cached_manifest_mtime = mtime
        return manifest

    def _collect_css(self, manifest: _Manifest, entrypoint: str) -> list[str]:
        visited: set[str] = set()
        css_files: list[str] = []

        def visit(key: str) -> None:
            if key in visited:
                return
            visited.add(key)

            entry = manifest.get(key)
            if not entry:
                return

            for css_file in entry.get("css", []):
                if css_file not in css_files:
                    css_files.append(css_file)

            for imported in entry.get("imports", []):
                visit(imported)

        visit(entrypoint)
        return css_files

    def _collect_modulepreload_files(self, manifest: _Manifest, entrypoint: str) -> list[str]:
        visited: set[str] = set()
        preload_files: list[str] = []

        def visit(key: str) -> None:
            if key in visited:
                return
            visited.add(key)

            entry = manifest.get(key)
            if not entry:
                return

            for imported in entry.get("imports", []):
                visit(imported)

            file = entry.get("file")
            if file and file not in preload_files:
                preload_files.append(file)

        for imported in manifest[entrypoint].get("imports", []):
            visit(imported)

        return preload_files

    def _static_url(self, asset_path: str) -> str:
        return f"{self._static_base_url}{asset_path.lstrip('/')}"

    @staticmethod
    def _css_tag(href: str) -> str:
        return f'<link rel="stylesheet" href="{escape(href)}" />'

    @staticmethod
    def _modulepreload_tag(href: str) -> str:
        return f'<link rel="modulepreload" href="{escape(href)}" crossorigin />'

    @staticmethod
    def _script_tag(src: str) -> str:
        return f'<script type="module" src="{escape(src)}"></script>'
