"""Sir Convert DigiExam migration contract constants.

Purpose:
  Centralize upstream DigiExam migration schema versions consumed by
  Skriptoteket curated apps so API models, projections, and tests bind to one
  generated-ready contract surface.

Relationships:
  - Mirrors Sir Convert's OpenAPI `x-sir-convert-digiexam-schema-versions`
    extension for the public Exam Converter and Conversion Hub lanes.
  - Imported by backend API contracts and persistence metadata validators.
"""

from __future__ import annotations

from typing import Final, Literal, TypeAlias

DigiExamMigrationBundleSchemaVersion: TypeAlias = Literal["digiexam_migration_bundle_v3"]
DigiExamEffectiveExamSchemaVersion: TypeAlias = Literal["digiexam_effective_exam_v2"]
DigiExamIntermediateExamSchemaVersion: TypeAlias = Literal["digiexam_intermediate_exam_v3"]
DigiExamIrManifestSchemaVersion: TypeAlias = Literal["digiexam_ir_manifest_v3"]

DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION: Final[DigiExamMigrationBundleSchemaVersion] = (
    "digiexam_migration_bundle_v3"
)
DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION: Final[DigiExamEffectiveExamSchemaVersion] = (
    "digiexam_effective_exam_v2"
)
DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION: Final[DigiExamIntermediateExamSchemaVersion] = (
    "digiexam_intermediate_exam_v3"
)
DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION: Final[DigiExamIrManifestSchemaVersion] = (
    "digiexam_ir_manifest_v3"
)
