"""DigiExam exam-conversion schema-version authority.

Purpose:
    Centralize the DigiExam conversion artifact schema versions shared by
    parser IR, ingestion overlays, effective exams, and overlay reports.

Relationships:
    - Imported by the exam-conversion domain contracts that expose artifact
      schema versions.
    - Mirrors the Sir Convert-a-Lot schema versions at revision 41be61a6 so
      overlay and effective-exam artifacts stay byte-compatible.
"""

from __future__ import annotations

from typing import Final, Literal, TypeAlias

DigiExamIntermediateExamSchemaVersion: TypeAlias = Literal["digiexam_intermediate_exam_v3"]
DigiExamIrManifestSchemaVersion: TypeAlias = Literal["digiexam_ir_manifest_v3"]
DigiExamIngestionOverlaySchemaVersion: TypeAlias = Literal["digiexam_ingestion_overlay_v2"]
DigiExamEffectiveExamSchemaVersion: TypeAlias = Literal["digiexam_effective_exam_v2"]
IngestionOverlayReportSchemaVersion: TypeAlias = Literal["ingestion_overlay_report_v1"]

DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION: Final[DigiExamIntermediateExamSchemaVersion] = (
    "digiexam_intermediate_exam_v3"
)
DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION: Final[DigiExamIrManifestSchemaVersion] = (
    "digiexam_ir_manifest_v3"
)
DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION: Final[DigiExamIngestionOverlaySchemaVersion] = (
    "digiexam_ingestion_overlay_v2"
)
DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION: Final[DigiExamEffectiveExamSchemaVersion] = (
    "digiexam_effective_exam_v2"
)
INGESTION_OVERLAY_REPORT_SCHEMA_VERSION: Final[IngestionOverlayReportSchemaVersion] = (
    "ingestion_overlay_report_v1"
)
