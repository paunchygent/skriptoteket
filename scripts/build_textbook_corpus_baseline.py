"""Build an immutable textbook corpus baseline with job-state reconciliation.

Purpose:
    Create a copy-only baseline package from textbook conversion artifacts before any cleanup work.
    The baseline preserves manifests, source files, local outputs, and service reconciliation payloads.

Relationships:
    - Reads Sir Convert-a-Lot manifest files from a source directory.
    - Optionally queries Sir Convert-a-Lot v2 job/result/artifact endpoints for reconciliation.
    - Writes a deterministic baseline package under an output directory.
    - Writes checksums and reconciliation metadata for downstream validation and auditability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import requests

DEFAULT_SERVICE_URL = "http://127.0.0.1:28085"
DEFAULT_OUTPUT_DIR = Path(".artifacts/textbook_corpus/baseline")
DEFAULT_MANIFEST_GLOB = "sir_convert_a_lot_manifest*.json"
TERMINAL_STATUSES = {"succeeded", "failed", "canceled", "cancelled"}
RECONCILE_ERROR_CODES = {"job_timeout", "job_poll_window_exceeded"}


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """Represents one conversion entry from a CLI manifest."""

    manifest_name: str
    source_root: str | None
    source_file_path: str | None
    output_path: str | None
    job_id: str | None
    status: str | None
    error_code: str | None
    pipeline_used: str | None
    source_format: str | None
    target_format: str | None


@dataclass(frozen=True, slots=True)
class SnapshotRecord:
    """Represents one file snapshot and its checksum metadata."""

    relative_path: str
    source_path: str | None
    sha256: str
    size_bytes: int


class ServiceClientProtocol(Protocol):
    """Protocol for job reconciliation calls."""

    def get_job(self, job_id: str) -> dict[str, Any]:
        """Return v2 job payload for a job id."""

    def get_result(self, job_id: str) -> dict[str, Any]:
        """Return v2 result payload for a job id."""

    def fetch_artifact(self, job_id: str) -> bytes:
        """Return binary artifact payload for a succeeded job."""


class ServiceClient(ServiceClientProtocol):
    """HTTP client for Sir Convert-a-Lot v2 reconciliation endpoints."""

    def __init__(self, *, service_url: str, api_key: str) -> None:
        self._base_url = service_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"X-API-Key": api_key})

    def get_job(self, job_id: str) -> dict[str, Any]:
        response = self._session.get(f"{self._base_url}/v2/convert/jobs/{job_id}", timeout=30)
        response.raise_for_status()
        return _as_object(response.json())

    def get_result(self, job_id: str) -> dict[str, Any]:
        response = self._session.get(
            f"{self._base_url}/v2/convert/jobs/{job_id}/result", timeout=30
        )
        response.raise_for_status()
        return _as_object(response.json())

    def fetch_artifact(self, job_id: str) -> bytes:
        response = self._session.get(
            f"{self._base_url}/v2/convert/jobs/{job_id}/artifact",
            timeout=120,
        )
        response.raise_for_status()
        return response.content


def _as_object(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest-glob", default=DEFAULT_MANIFEST_GLOB)
    parser.add_argument("--service-url", default=DEFAULT_SERVICE_URL)
    parser.add_argument(
        "--api-key",
        default="",
        help="Sir Convert-a-Lot v2 API key. Defaults to SIR_CONVERT_A_LOT_V2_API_KEY env var.",
    )
    parser.add_argument(
        "--fetch-missing-artifacts",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "When reconciliation shows succeeded jobs without local outputs, fetch artifact copies "
            "into the baseline package."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print reconciliation summary without writing files.",
    )
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help=(
            "Allow writing into a non-empty output directory. "
            "Default behavior fails closed to protect immutable baselines."
        ),
    )
    return parser.parse_args()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _as_object(payload)


def _load_manifest_entries(source_dir: Path, manifest_glob: str) -> list[ManifestEntry]:
    entries: list[ManifestEntry] = []
    for manifest_path in sorted(source_dir.glob(manifest_glob)):
        payload = _read_json(manifest_path)
        source_root_obj = payload.get("source_root")
        source_root = str(source_root_obj) if isinstance(source_root_obj, str) else None
        entries_obj = payload.get("entries")
        if not isinstance(entries_obj, list):
            continue
        for row in entries_obj:
            item = _as_object(row)
            entries.append(
                ManifestEntry(
                    manifest_name=manifest_path.name,
                    source_root=source_root,
                    source_file_path=_as_optional_string(item.get("source_file_path")),
                    output_path=_as_optional_string(item.get("output_path")),
                    job_id=_as_optional_string(item.get("job_id")),
                    status=_as_optional_string(item.get("status")),
                    error_code=_as_optional_string(item.get("error_code")),
                    pipeline_used=_as_optional_string(item.get("pipeline_used")),
                    source_format=_as_optional_string(item.get("source_format")),
                    target_format=_as_optional_string(item.get("target_format")),
                )
            )
    return entries


def _as_optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _copy_bytes(
    *,
    payload: bytes,
    output_dir: Path,
    relative_path: Path,
    source_path: str | None,
    records: list[SnapshotRecord],
    dry_run: bool,
) -> None:
    destination = output_dir / relative_path
    records.append(
        SnapshotRecord(
            relative_path=relative_path.as_posix(),
            source_path=source_path,
            sha256=_sha256_bytes(payload),
            size_bytes=len(payload),
        )
    )
    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)


def _resolve_source_file_path(entry: ManifestEntry, source_dir: Path) -> Path | None:
    if not entry.source_file_path:
        return None
    source_path = Path(entry.source_file_path)
    if source_path.is_absolute():
        return source_path if source_path.is_file() else None

    if entry.source_root:
        root_path = Path(entry.source_root)
        if root_path.is_file():
            if root_path.name == source_path.name:
                return root_path
        elif root_path.is_dir():
            candidate = root_path / source_path
            if candidate.is_file():
                return candidate

    candidate_from_source_dir = source_dir / source_path
    if candidate_from_source_dir.is_file():
        return candidate_from_source_dir
    return None


def _needs_reconciliation(entry: ManifestEntry) -> bool:
    status = (entry.status or "").lower()
    error_code = (entry.error_code or "").lower()
    if entry.job_id is None:
        return False
    if status not in TERMINAL_STATUSES:
        return True
    return error_code in RECONCILE_ERROR_CODES


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)


def _save_json(payload: dict[str, Any], destination: Path, dry_run: bool) -> None:
    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _ensure_output_dir_safe(*, output_dir: Path, allow_overwrite: bool, dry_run: bool) -> None:
    if dry_run:
        return
    if output_dir.exists() and not output_dir.is_dir():
        raise SystemExit(f"Output path exists and is not a directory: {output_dir}")
    if output_dir.exists() and any(output_dir.iterdir()) and not allow_overwrite:
        raise SystemExit(
            "Refusing to overwrite non-empty baseline output directory. "
            "Use --allow-overwrite only when you have explicitly archived/verified prior baseline output."
        )
    output_dir.mkdir(parents=True, exist_ok=True)


def build_baseline(
    *,
    source_dir: Path,
    output_dir: Path,
    manifest_glob: str,
    service_client: ServiceClientProtocol | None,
    fetch_missing_artifacts: bool,
    allow_overwrite: bool,
    dry_run: bool,
) -> dict[str, Any]:
    _ensure_output_dir_safe(
        output_dir=output_dir,
        allow_overwrite=allow_overwrite,
        dry_run=dry_run,
    )

    manifest_paths = sorted(source_dir.glob(manifest_glob))
    entries = _load_manifest_entries(source_dir, manifest_glob)
    checksum_records: list[SnapshotRecord] = []
    reconciliation_rows: list[dict[str, Any]] = []

    for manifest_path in manifest_paths:
        _copy_bytes(
            payload=manifest_path.read_bytes(),
            output_dir=output_dir,
            relative_path=Path("raw/manifests") / manifest_path.name,
            source_path=str(manifest_path),
            records=checksum_records,
            dry_run=dry_run,
        )

    for entry in entries:
        issues: list[str] = []
        local_output_exists = False
        local_output_snapshot_path: str | None = None
        source_snapshot_path: str | None = None
        fetched_artifact_snapshot_path: str | None = None

        source_file = _resolve_source_file_path(entry, source_dir)
        if source_file is not None:
            source_snapshot_rel = (
                Path("raw/sources") / _safe_slug(entry.manifest_name) / source_file.name
            )
            _copy_bytes(
                payload=source_file.read_bytes(),
                output_dir=output_dir,
                relative_path=source_snapshot_rel,
                source_path=str(source_file),
                records=checksum_records,
                dry_run=dry_run,
            )
            source_snapshot_path = source_snapshot_rel.as_posix()
        else:
            issues.append("missing_source_file")

        local_output_path = Path(entry.output_path) if entry.output_path else None
        if local_output_path and local_output_path.is_file():
            local_output_exists = True
            output_name = local_output_path.name
            output_snapshot_rel = Path("raw/outputs/local") / (
                f"{entry.job_id or 'no_job'}__{_safe_slug(output_name)}"
            )
            _copy_bytes(
                payload=local_output_path.read_bytes(),
                output_dir=output_dir,
                relative_path=output_snapshot_rel,
                source_path=str(local_output_path),
                records=checksum_records,
                dry_run=dry_run,
            )
            local_output_snapshot_path = output_snapshot_rel.as_posix()

        reconciled_status = entry.status
        reconcile_attempted = False
        job_payload: dict[str, Any] | None = None
        result_payload: dict[str, Any] | None = None

        if _needs_reconciliation(entry):
            reconcile_attempted = True
            if service_client is None:
                issues.append("reconciliation_skipped_missing_api_key")
            else:
                try:
                    job_payload = service_client.get_job(entry.job_id or "")
                    result_payload = service_client.get_result(entry.job_id or "")
                    job_obj = _as_object(job_payload.get("job"))
                    reconciled_status = _as_optional_string(job_obj.get("status")) or entry.status

                    if entry.job_id:
                        _save_json(
                            job_payload,
                            output_dir / "provenance/jobs" / f"{entry.job_id}.job.json",
                            dry_run,
                        )
                        _save_json(
                            result_payload,
                            output_dir / "provenance/jobs" / f"{entry.job_id}.result.json",
                            dry_run,
                        )
                except requests.RequestException:
                    issues.append("reconciliation_http_error")
                except json.JSONDecodeError:
                    issues.append("reconciliation_json_error")

        normalized_reconciled = (reconciled_status or "").lower()
        if (
            fetch_missing_artifacts
            and entry.job_id
            and normalized_reconciled == "succeeded"
            and not local_output_exists
            and service_client is not None
        ):
            try:
                artifact_bytes = service_client.fetch_artifact(entry.job_id)
                target_suffix = _target_suffix(entry.target_format)
                output_name = f"{entry.job_id}{target_suffix}"
                fetched_rel = Path("raw/outputs/fetched") / output_name
                _copy_bytes(
                    payload=artifact_bytes,
                    output_dir=output_dir,
                    relative_path=fetched_rel,
                    source_path=f"{entry.job_id}:artifact",
                    records=checksum_records,
                    dry_run=dry_run,
                )
                fetched_artifact_snapshot_path = fetched_rel.as_posix()
            except requests.RequestException:
                issues.append("artifact_fetch_http_error")

        reconciliation_rows.append(
            {
                "manifest_name": entry.manifest_name,
                "job_id": entry.job_id,
                "status_manifest": entry.status,
                "status_reconciled": reconciled_status,
                "error_code_manifest": entry.error_code,
                "reconcile_attempted": reconcile_attempted,
                "source_file_path": entry.source_file_path,
                "source_snapshot_path": source_snapshot_path,
                "output_path": entry.output_path,
                "local_output_exists": local_output_exists,
                "local_output_snapshot_path": local_output_snapshot_path,
                "fetched_artifact_snapshot_path": fetched_artifact_snapshot_path,
                "pipeline_used": entry.pipeline_used,
                "source_format": entry.source_format,
                "target_format": entry.target_format,
                "issues": sorted(set(issues)),
            }
        )

    report_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_dir": str(source_dir),
        "manifest_glob": manifest_glob,
        "entries_total": len(entries),
        "summary": _summarize_rows(reconciliation_rows),
        "reconciliation_rows": reconciliation_rows,
    }
    checksums_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "output_dir": str(output_dir),
        "files": [
            {
                "relative_path": record.relative_path,
                "source_path": record.source_path,
                "sha256": record.sha256,
                "size_bytes": record.size_bytes,
            }
            for record in sorted(checksum_records, key=lambda item: item.relative_path)
        ],
    }

    _save_json(report_payload, output_dir / "provenance/reconciliation-report.json", dry_run)
    _save_json(checksums_payload, output_dir / "checksums.json", dry_run)
    return {"report": report_payload, "checksums": checksums_payload}


def _target_suffix(target_format: str | None) -> str:
    lookup = {"md": ".md", "pdf": ".pdf", "docx": ".docx"}
    if target_format is None:
        return ".bin"
    return lookup.get(target_format.lower(), ".bin")


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {
        "reconcile_attempted": 0,
        "local_output_exists": 0,
        "fetched_artifact_count": 0,
    }
    for row in rows:
        if bool(row.get("reconcile_attempted")):
            summary["reconcile_attempted"] += 1
        if bool(row.get("local_output_exists")):
            summary["local_output_exists"] += 1
        if isinstance(row.get("fetched_artifact_snapshot_path"), str):
            summary["fetched_artifact_count"] += 1

        status = str(row.get("status_reconciled") or "unknown").lower()
        key = f"status_{status}"
        summary[key] = summary.get(key, 0) + 1
    return summary


def main() -> None:
    args = _parse_args()
    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    api_key = args.api_key.strip() or ""
    api_key = api_key or _as_optional_string(os.environ.get("SIR_CONVERT_A_LOT_V2_API_KEY")) or ""

    service_client: ServiceClientProtocol | None = None
    if api_key:
        service_client = ServiceClient(service_url=args.service_url, api_key=api_key)

    payload = build_baseline(
        source_dir=source_dir,
        output_dir=output_dir,
        manifest_glob=args.manifest_glob,
        service_client=service_client,
        fetch_missing_artifacts=bool(args.fetch_missing_artifacts),
        allow_overwrite=bool(args.allow_overwrite),
        dry_run=bool(args.dry_run),
    )

    report_summary = _as_object(_as_object(payload["report"]).get("summary"))
    print(f"[textbook_baseline] output_dir={output_dir}")
    print(f"[textbook_baseline] entries_total={_as_object(payload['report']).get('entries_total')}")
    print(
        f"[textbook_baseline] summary={json.dumps(report_summary, ensure_ascii=False, sort_keys=True)}"
    )
    if not api_key:
        print("[textbook_baseline] warning=no_api_key_reconciliation_limited=true")


if __name__ == "__main__":
    main()
