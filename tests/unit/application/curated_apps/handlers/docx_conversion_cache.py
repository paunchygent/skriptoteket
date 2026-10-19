"""One default replay conversion per exam, shared by every test file and every xdist worker.

A default conversion (recorded replies, nothing corrupted) of one exam takes seconds, and the
tests of the exam converter read the same result many times. The first test that asks converts
the exam and stores the immutable result in the pytest run's shared temporary directory; every
later test, on any worker, unpickles its own copy. The directory belongs to one pytest run, so
a result never outlives the code that produced it.
"""

from __future__ import annotations

import io
import os
import pickle
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest
from filelock import FileLock

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionOutcome,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMRequest,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import build_replay


@dataclass(frozen=True)
class ProviderTrace:
    """What the replay provider saw and served during one conversion."""

    requests: tuple[StructuredLLMRequest, ...]
    recording_ids: Mapping[str, str]
    served: tuple[tuple[str, str], ...]

    @property
    def request_ids(self) -> list[str]:
        return [request.item_id for request in self.requests]


@dataclass(frozen=True)
class ProgressTrace:
    """The progress-port calls and batch updates of one conversion."""

    calls: tuple[str, ...]
    updates: tuple[ConversionUpdate, ...]


@dataclass(frozen=True)
class ConvertedExam:
    """The outcome of one default conversion and the traces of its doubles."""

    exam: str
    outcome: DocxConversionOutcome
    provider: ProviderTrace
    progress: ProgressTrace


def _read_only(data: dict[Any, Any]) -> MappingProxyType[Any, Any]:
    return MappingProxyType(data)


def _reduce_mapping_proxy(proxy: MappingProxyType[Any, Any]) -> tuple[Any, ...]:
    return (_read_only, (dict(proxy),))


def _dump(converted: ConvertedExam) -> bytes:
    """Pickle ``converted``; read-only mapping views, which pickle refuses, round-trip as such."""
    buffer = io.BytesIO()
    pickler = pickle.Pickler(buffer)
    pickler.dispatch_table = {MappingProxyType: _reduce_mapping_proxy}  # type: ignore[attr-defined]
    pickler.dump(converted)
    return buffer.getvalue()


class ConversionCache:
    """Converts an exam once per pytest run; every caller gets its own unpickled copy."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    async def converted(self, exam: str) -> ConvertedExam:
        self._directory.mkdir(parents=True, exist_ok=True)
        stored = self._directory / f"{exam}.pickle"
        with FileLock(self._directory / f"{exam}.lock"):
            if not stored.exists():
                replay = build_replay(exam)
                outcome = await replay.pipeline.convert(job=replay.job())
                converted = ConvertedExam(
                    exam=exam,
                    outcome=outcome,
                    provider=ProviderTrace(
                        requests=tuple(replay.provider.requests),
                        recording_ids=dict(replay.provider.recording_ids),
                        served=tuple(replay.provider.served),
                    ),
                    progress=ProgressTrace(
                        calls=tuple(replay.progress.calls),
                        updates=tuple(replay.progress.updates),
                    ),
                )
                partial = stored.with_suffix(".partial")
                partial.write_bytes(_dump(converted))
                partial.replace(stored)
            loaded: ConvertedExam = pickle.loads(stored.read_bytes())  # noqa: S301
        return loaded


@pytest.fixture(name="conversions", scope="session")
def conversion_cache_fixture(tmp_path_factory: pytest.TempPathFactory) -> ConversionCache:
    root = tmp_path_factory.getbasetemp()
    if os.environ.get("PYTEST_XDIST_WORKER"):
        root = root.parent
    return ConversionCache(root / "docx_conversions")
