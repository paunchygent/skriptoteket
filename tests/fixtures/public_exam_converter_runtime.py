"""Focused artifact fixtures for the public Exam Converter runtime tests."""

from skriptoteket.application.curated_apps.exam_conversion import (
    ExamConversionNamedArtifact,
    ExamConversionStoredArtifact,
)
from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterUpload,
)


def local_public_exam_artifact(
    *,
    source_dxe: PublicExamConverterUpload,
) -> ExamConversionStoredArtifact:
    return ExamConversionStoredArtifact(
        filename="examnet-bundle.zip",
        content_type="application/zip",
        content=b"local bundle",
        source_filename=source_dxe.filename,
        source_content=source_dxe.file_bytes,
        named_artifacts=(
            ExamConversionNamedArtifact(
                artifact_key="examnet_pdf",
                filename="examnet-import.pdf",
                content_type="application/pdf",
                content=b"%PDF fake",
            ),
            ExamConversionNamedArtifact(
                artifact_key="qti_package",
                filename="qti-package.zip",
                content_type="application/zip",
                content=b"qti package",
            ),
            ExamConversionNamedArtifact(
                artifact_key="target_readiness_report",
                filename="target-readiness-report.json",
                content_type="application/json",
                content=(
                    b'{"targets":[{"target":"examnet_pdf","item_id":null,"export_enabled":true}]}'
                ),
            ),
            ExamConversionNamedArtifact(
                artifact_key="ir_json",
                filename="exam-ir.json",
                content_type="application/json",
                content=b"{}",
            ),
            ExamConversionNamedArtifact(
                artifact_key="source_ir_json",
                filename="source-ir.json",
                content_type="application/json",
                content=(
                    b'{"warnings":[{"code":"unsupported_source_fragment",'
                    b'"message":"One source fragment requires review."}]}'
                ),
            ),
        ),
    )
