"""Read-side contracts for importing a QTI 3.0 package into the exam workspace.

Purpose:
    Define the value objects a package reader hands to the native exam mapper:
    the item XML files the assessment test names in test order, every other file
    by normalized package-relative path, and the unsupported items or item
    children the mapper skips with a visible note.

Relationships:
    - Produced by the QTI package readers (zip and XML parsing).
    - Consumed by ``exam_workspace.qti_import``; ``ExamNetQtiReadItem`` reuses
      the write-side ``ExamNetQtiItem`` so import inverts exactly what export
      produces.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiItem,
)


@dataclass(frozen=True)
class ExamNetQtiPackageItemSource:
    """One item XML file the package's assessment test names, in test order."""

    path: str
    xml: bytes


@dataclass(frozen=True)
class ExamNetQtiPackageSource:
    """A read QTI package: item XML in test order and every package file by path."""

    items: tuple[ExamNetQtiPackageItemSource, ...]
    files: Mapping[str, bytes]


class ExamNetQtiUnsupportedReason(StrEnum):
    """Why the import skips one package item or one of its children."""

    INTERACTION = "interaction"
    IMAGE = "image"


@dataclass(frozen=True)
class ExamNetQtiUnsupportedItem:
    """One package item, or one child of it, that the import skips with a note."""

    sequence: int
    opening_text: str
    reason: ExamNetQtiUnsupportedReason


ExamNetQtiReadItem: TypeAlias = ExamNetQtiItem | ExamNetQtiUnsupportedItem
