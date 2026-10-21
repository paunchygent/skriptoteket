"""DigiExam exam-conversion schema-version authority.

Purpose:
    Centralize the DigiExam conversion artifact schema versions shared by
    parser IR and its manifest.

Relationships:
    - Imported by the exam-conversion domain contracts that expose artifact
      schema versions.
"""

from __future__ import annotations

from typing import Final, Literal, TypeAlias

DigiExamIntermediateExamSchemaVersion: TypeAlias = Literal["digiexam_intermediate_exam_v3"]
DigiExamIrManifestSchemaVersion: TypeAlias = Literal["digiexam_ir_manifest_v3"]

DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION: Final[DigiExamIntermediateExamSchemaVersion] = (
    "digiexam_intermediate_exam_v3"
)
DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION: Final[DigiExamIrManifestSchemaVersion] = (
    "digiexam_ir_manifest_v3"
)
