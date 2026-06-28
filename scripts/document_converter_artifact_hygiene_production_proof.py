"""Native production proof for Document Converter artifact hygiene.

Domain purpose:
    Exercise deployed Document Converter application handlers on Hemma and
    retain redacted evidence that teacher-facing artifacts do not leak internal
    conversion stems, placeholders, raw ids, or checkpoint comments.

Relationships:
    - Runs inside the deployed Skriptoteket web container after commit, push,
      and redeploy.
    - Uses the same Dishka request-scoped handlers as the protected API routes.
    - Complements the browser proof helper by proving artifact bytes and
      metadata directly when production browser credentials are unavailable.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import time
import zipfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from dishka import Scope
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJobSpecV2,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
    build_conversion_hub_v2_job_spec,
)
from skriptoteket.application.curated_apps.document_converter_projects import (
    DocumentConverterProjectManifest,
    DocumentConverterProjectOutputMode,
    DocumentConverterProjectUploadedFile,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_document_converter import (
    DownloadDocumentConverterArtifactHandler,
    GetDocumentConverterJobHandler,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
)
from skriptoteket.application.curated_apps.handlers.document_converter_jobs import (
    CreateDocumentConverterJobsHandler,
)
from skriptoteket.application.curated_apps.handlers.document_converter_project_previews import (
    DownloadDocumentConverterProjectPreviewArtifactHandler,
    RenderDocumentConverterProjectPreviewHandler,
)
from skriptoteket.config import Settings
from skriptoteket.di import create_container
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.db.models.user import UserModel

FORBIDDEN_MARKERS = (
    "pdf_checkpointed_output",
    "sir-convert-a-lot:partial",
    "__missing_asset__",
    "Bild saknas",
    "Saknad resurs",
)

_FIXTURE_IMAGE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAApElEQVR4nO3aQQ6AIAwF0dr7"
    "H7u7MRMbWq0kJPpB0gyY/ENJ4x6A6f0G4N3YA+gB9AB6AD2AHkAPoAfQA+gB9AB6AD2"
    "AHkAPoAfQA+gB9AB6AD2AHkAPoAfQA+gB9AB6AD2AHkAPoAfQA+gB9AB6AD2AHkAPoA"
    "fQA+gB9AB6AD2AHkAPoAfQA+gB9AB6AD2AHkAPoAfQA+gB9AB6AD2AHkAPoAfQA+gB9"
    "AB6AD2AHkAPoAfQA+gB9AB6AD2AHoBv7QFxXgNNmcnYpQAAAABJRU5ErkJggg=="
)


def parse_args() -> argparse.Namespace:
    """Parse the native proof runner arguments."""
    parser = argparse.ArgumentParser(
        description="Run native production Document Converter artifact hygiene proof."
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--single-file-timeout-seconds", default=180, type=int)
    return parser.parse_args()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a stable JSON evidence file."""
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def marker_hits_in_text(text: str) -> list[str]:
    """Return forbidden marker strings found in text."""
    return sorted(marker for marker in FORBIDDEN_MARKERS if marker in text)


def marker_hits_in_bytes(content: bytes) -> list[str]:
    """Return forbidden marker strings found in bytes."""
    return sorted(marker for marker in FORBIDDEN_MARKERS if marker.encode("utf-8") in content)


def inspect_pdf(content: bytes) -> dict[str, Any]:
    """Inspect PDF text and metadata for forbidden markers."""
    reader = PdfReader(io.BytesIO(content))
    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    compact_text = " ".join(extracted_text.split())
    metadata = reader.metadata or {}
    metadata_text = "\n".join(str(value) for value in metadata.values() if value is not None)
    return {
        "metadata_marker_hits": marker_hits_in_text(metadata_text),
        "page_count": len(reader.pages),
        "text_excerpt": compact_text[:320],
        "text_marker_hits": marker_hits_in_text(compact_text),
    }


def inspect_zip_text_members(content: bytes) -> dict[str, Any]:
    """Inspect text-like ZIP members such as DOCX XML for forbidden markers."""
    hits: dict[str, list[str]] = {}
    member_count = 0
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for name in archive.namelist():
            member_count += 1
            if not name.endswith((".xml", ".rels", ".txt", ".md", ".html", ".htm")):
                continue
            text = archive.read(name).decode("utf-8", errors="replace")
            member_hits = marker_hits_in_text(text)
            if member_hits:
                hits[name] = member_hits
    return {"zip_member_count": member_count, "zip_text_marker_hits": hits}


def inspect_artifact(
    *,
    output_dir: Path,
    label: str,
    filename: str,
    content_type: str,
    content: bytes,
) -> dict[str, Any]:
    """Persist one artifact and return redacted hygiene inspection metadata."""
    suffix = Path(filename).suffix or ".bin"
    artifact_path = output_dir / f"{label}{suffix}"
    artifact_path.write_bytes(content)
    raw_hits = marker_hits_in_bytes(content)
    result: dict[str, Any] = {
        "content_type": content_type,
        "filename": filename,
        "path": str(artifact_path),
        "raw_marker_hits": raw_hits,
        "sha256": sha256(content).hexdigest(),
        "size_bytes": len(content),
    }
    if content_type.startswith("application/pdf") or suffix.lower() == ".pdf":
        result["pdf"] = inspect_pdf(content)
    if suffix.lower() in {".docx", ".pptx", ".xlsx", ".zip"}:
        result["zip"] = inspect_zip_text_members(content)
    result["forbidden_marker_hits"] = sorted(
        set(marker_hits_in_text(json.dumps(result, ensure_ascii=False)) + raw_hits)
    )
    return result


async def load_actor(container: Any) -> User:
    """Select one active production user for owner-scoped handler proof."""
    async with container(scope=Scope.REQUEST) as request:
        session = await request.get(AsyncSession)
        result = await session.execute(
            select(UserModel)
            .where(UserModel.is_active.is_(True))
            .order_by(UserModel.created_at.asc())
            .limit(1)
        )
        model = result.scalar_one()
        return User.model_validate(model)


def build_project_fixture() -> tuple[
    DocumentConverterProjectManifest,
    list[DocumentConverterProjectUploadedFile],
]:
    """Build an HTML/CSS project with declared real image bytes."""
    html = """<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <title>PR-0400 Hemma project proof</title>
  <link rel="stylesheet" href="project:///styles.css">
</head>
<body>
  <main class="sheet">
    <h1>PR-0400 Hemma project proof</h1>
    <p class="callout">Real uploaded image bytes and CSS are rendered.</p>
    <img src="project:///cover.png" alt="Uploaded proof image">
  </main>
</body>
</html>
"""
    css = """body { margin: 0; padding: 24mm; color: #18314f; background: #fffdf8; }
.sheet { border: 2mm solid #18314f; padding: 10mm; }
.callout { background: #f47b52; color: #ffffff; padding: 5mm; font-weight: 700; }
img { width: 32mm; height: 32mm; border: 1mm solid #0e8f5a; }
"""
    manifest = DocumentConverterProjectManifest.model_validate(
        {
            "css_files": ["styles.css"],
            "font_files": [],
            "html_entries": [{"entry_id": "hemma-project", "filename": "hemma-project.html"}],
            "image_files": ["cover.png"],
            "output_mode": DocumentConverterProjectOutputMode.BOTH.value,
            "pdf_controls": {
                "margins": {"bottom_mm": 12, "left_mm": 12, "right_mm": 12, "top_mm": 12},
                "orientation": "portrait",
                "paper_size": "a4",
                "template_id": "academic_phd",
            },
        }
    )
    files = [
        DocumentConverterProjectUploadedFile(
            filename="hemma-project.html",
            content=html.encode("utf-8"),
            content_type="text/html",
        ),
        DocumentConverterProjectUploadedFile(
            filename="styles.css",
            content=css.encode("utf-8"),
            content_type="text/css",
        ),
        DocumentConverterProjectUploadedFile(
            filename="cover.png",
            content=_FIXTURE_IMAGE_PNG,
            content_type="image/png",
        ),
    ]
    return manifest, files


async def run_project_preview(
    container: Any,
    *,
    actor: User,
    output_dir: Path,
) -> dict[str, Any]:
    """Render and download project-preview artifacts through production handlers."""
    manifest, files = build_project_fixture()
    async with container(scope=Scope.REQUEST) as request:
        render = await request.get(RenderDocumentConverterProjectPreviewHandler)
        download = await request.get(DownloadDocumentConverterProjectPreviewArtifactHandler)
        preview = await render.handle(actor=actor, manifest=manifest, files=files)
        artifacts = []
        for index, artifact_ref in enumerate(preview.artifacts):
            artifact = await download.handle(
                actor=actor,
                artifact_id=artifact_ref.artifact_id,
                preview_id=preview.preview_id,
            )
            artifacts.append(
                inspect_artifact(
                    output_dir=output_dir,
                    label=f"project-preview-{index}-{artifact_ref.kind.value}",
                    filename=artifact.filename,
                    content_type=artifact.content_type,
                    content=artifact.content,
                )
            )
        return {
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
            "output_mode": preview.output_mode.value,
            "preview_id_hash": sha256(str(preview.preview_id).encode("utf-8")).hexdigest()[:16],
            "status": preview.status.value,
        }


async def run_single_file_conversion(
    container: Any,
    *,
    actor: User,
    output_dir: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Submit and download one Sir Convert-backed HTML-to-DOCX artifact."""
    spec = ConversionHubJobSpecV2(
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=ConversionHubOutputFormatV2.DOCX,
        pdf_layout=None,
    )
    html = (
        b"<!doctype html><html><head><meta charset='utf-8'></head><body>"
        b"<h1>PR-0400 Sir Convert proof</h1><p>Terminal artifact cleanliness.</p>"
        b"</body></html>"
    )
    upload = ConversionHubUpload(
        filename="pr-0400-sir-convert-proof.html",
        content_type="text/html",
        file_bytes=html,
    )
    async with container(scope=Scope.REQUEST) as request:
        create = await request.get(CreateDocumentConverterJobsHandler)
        get_status = await request.get(GetDocumentConverterJobHandler)
        download = await request.get(DownloadDocumentConverterArtifactHandler)
        submitted = await create.handle(
            actor=actor,
            build_job_spec=build_conversion_hub_v2_job_spec,
            correlation_id="pr-0400-production-proof",
            spec=spec,
            uploads=[upload],
            wait_seconds=20,
        )
        job = submitted.jobs[0]
        status = await get_status.handle(
            actor=actor,
            correlation_id="pr-0400-production-proof",
            job_id=job.job_id,
        )
        deadline = time.monotonic() + timeout_seconds
        terminal = {
            ConversionHubJobStatus.CANCELED,
            ConversionHubJobStatus.FAILED,
            ConversionHubJobStatus.SUCCEEDED,
        }
        while status.status not in terminal:
            if time.monotonic() >= deadline:
                raise AssertionError(
                    f"Timed out waiting for Sir Convert-backed job: {status.status.value}"
                )
            await asyncio.sleep(2)
            status = await get_status.handle(
                actor=actor,
                correlation_id="pr-0400-production-proof",
                job_id=job.job_id,
            )
        if status.status is not ConversionHubJobStatus.SUCCEEDED:
            raise AssertionError(
                f"Sir Convert-backed job did not succeed: {status.status.value} {status.error!r}"
            )
        filename, content_type, content = await download.handle(
            actor=actor,
            correlation_id="pr-0400-production-proof",
            job_id=job.job_id,
        )
        artifact = inspect_artifact(
            output_dir=output_dir,
            label="single-file-sir-convert",
            filename=filename,
            content_type=content_type,
            content=content,
        )
        return {
            "artifact": artifact,
            "job_id_hash": sha256(str(job.job_id).encode("utf-8")).hexdigest()[:16],
            "producer": job.producer.value,
            "producer_reason": job.producer_reason,
            "status": status.status.value,
        }


def assert_clean(summary: dict[str, Any]) -> None:
    """Fail if any retained artifact inspection found forbidden markers."""
    dirty: list[str] = []
    for branch_name in ("project_preview", "single_file"):
        branch = summary[branch_name]
        artifacts = branch.get("artifacts") or [branch.get("artifact")]
        for artifact in artifacts:
            if not artifact:
                continue
            hits = artifact.get("forbidden_marker_hits") or []
            if hits:
                dirty.append(f"{branch_name}:{artifact.get('filename')}:{hits}")
    if dirty:
        raise AssertionError("Forbidden marker hits found: " + "; ".join(dirty))


async def run() -> int:
    """Run both production proof flows and retain a redacted manifest."""
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    container = create_container(settings)
    try:
        actor = await load_actor(container)
        summary: dict[str, Any] = {
            "actor_id_hash": sha256(str(actor.id).encode("utf-8")).hexdigest()[:16],
            "artifact_dir": str(output_dir),
            "forbidden_markers": list(FORBIDDEN_MARKERS),
            "settings": {
                "environment": settings.ENVIRONMENT,
                "service_name": settings.SERVICE_NAME,
                "sir_convert_base_url": settings.SIR_CONVERT_A_LOT_V2_BASE_URL,
            },
            "status": "running",
            "timestamp_utc": datetime.now(tz=UTC).isoformat(),
        }
        write_json(output_dir / "manifest.redacted.json", summary)
        summary["project_preview"] = await run_project_preview(
            container,
            actor=actor,
            output_dir=output_dir,
        )
        summary["single_file"] = await run_single_file_conversion(
            container,
            actor=actor,
            output_dir=output_dir,
            timeout_seconds=args.single_file_timeout_seconds,
        )
        assert_clean(summary)
        summary["status"] = "ok"
        write_json(output_dir / "manifest.redacted.json", summary)
    finally:
        await container.close()
    print(f"document-converter-artifact-hygiene-proof: ok artifact_dir={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
