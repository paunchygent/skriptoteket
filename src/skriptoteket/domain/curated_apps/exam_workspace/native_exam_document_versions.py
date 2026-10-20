"""Readable versions and the upgrade chain for stored native exam documents."""

import re
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Final

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

_VERSION_PATTERN = re.compile(r"native_exam_document_v(\d+)")


def native_exam_document_version(schema_version: object) -> int | None:
    if not isinstance(schema_version, str):
        return None
    match = _VERSION_PATTERN.fullmatch(schema_version)
    if match is None:
        return None
    return int(match.group(1))


def _current_version() -> int:
    version = native_exam_document_version(NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION)
    if version is None:
        raise RuntimeError("NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION has no version number.")
    return version


CURRENT_NATIVE_EXAM_DOCUMENT_VERSION: Final[int] = _current_version()

# Every stored document below this version cannot be read. Raising it is one
# deliberate edit; nothing is deleted automatically.
OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION: Final[int] = 10

# Reads the JSON object of version N and returns the JSON object of version N+1.
NativeExamDocumentUpgradeStep = Callable[[dict[str, object]], dict[str, object]]

# One step per version from the oldest readable one up to the current one,
# keyed by the version it reads; empty before release (ADR-SKRIPT-0093).
NATIVE_EXAM_DOCUMENT_UPGRADE_STEPS: Final[Mapping[int, NativeExamDocumentUpgradeStep]] = (
    MappingProxyType({})
)


def upgrade_native_exam_document_payload(
    payload: dict[str, object],
    *,
    version: int,
    steps: Mapping[int, NativeExamDocumentUpgradeStep] = NATIVE_EXAM_DOCUMENT_UPGRADE_STEPS,
    current: int = CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
) -> dict[str, object]:
    upgraded = payload
    for step_version in range(version, current):
        step = steps.get(step_version)
        if step is None:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Native exam document upgrade chain has a gap.",
                details={"version": step_version},
            )
        upgraded = step(upgraded)
    return upgraded


def is_readable_native_exam_document_version(version: int) -> bool:
    return (
        OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION
        <= version
        <= CURRENT_NATIVE_EXAM_DOCUMENT_VERSION
    )
