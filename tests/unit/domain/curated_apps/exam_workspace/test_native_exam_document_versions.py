"""Safeguard test for native exam document format versions (TASK-SKRIPT-41-02-06 U1)."""

import json
import re
from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_versions import (
    CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
    NATIVE_EXAM_DOCUMENT_UPGRADE_STEPS,
    OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION,
    is_readable_native_exam_document_version,
    native_exam_document_version,
    upgrade_native_exam_document_payload,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)

FIXTURE_DIR = (
    Path(__file__).resolve().parents[4] / "fixtures" / "exam_workspace" / "document_versions"
)
_SAMPLE_PATTERN = re.compile(r"native_exam_document_v(\d+)\.json")


def chain_gaps(
    *,
    oldest: int,
    current: int,
    step_versions: set[int],
    sample_versions: set[int],
) -> list[str]:
    problems: list[str] = []
    if oldest > current:
        problems.append(f"oldest readable version {oldest} is above current version {current}")
    for version in range(oldest, current):
        if version not in step_versions:
            problems.append(f"missing upgrade step for version {version}")
    for version in sorted(step_versions):
        if version < oldest or version >= current:
            problems.append(f"extra upgrade step for version {version}")
    for version in range(oldest, current + 1):
        if version not in sample_versions:
            problems.append(f"missing sample for version {version}")
    for version in sorted(sample_versions):
        if version < oldest or version > current:
            problems.append(f"extra sample for version {version}")
    return problems


def _sample_versions() -> set[int]:
    versions: set[int] = set()
    if FIXTURE_DIR.is_dir():
        for path in FIXTURE_DIR.iterdir():
            match = _SAMPLE_PATTERN.fullmatch(path.name)
            if match is not None:
                versions.add(int(match.group(1)))
    return versions


def _stored_payload_bytes(schema_version: object) -> bytes:
    payload = json.loads(
        native_exam_document_json_bytes(make_document(make_free_text_item())).decode("utf-8")
    )
    payload["schema_version"] = schema_version
    return json.dumps(payload).encode("utf-8")


class TestUpgradeChainSafeguard:
    def test_chain_has_no_gaps_and_every_sample_parses(self) -> None:
        problems = chain_gaps(
            oldest=OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION,
            current=CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
            step_versions=set(NATIVE_EXAM_DOCUMENT_UPGRADE_STEPS),
            sample_versions=_sample_versions(),
        )
        assert problems == []
        for version in range(
            OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION,
            CURRENT_NATIVE_EXAM_DOCUMENT_VERSION + 1,
        ):
            data = (FIXTURE_DIR / f"native_exam_document_v{version}.json").read_bytes()
            assert parse_native_exam_document(data).schema_version == (
                NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION
            )


class TestChainGapsChecker:
    def test_raising_current_without_step_or_sample_reports_both(self) -> None:
        assert chain_gaps(oldest=10, current=11, step_versions=set(), sample_versions={10}) == [
            "missing upgrade step for version 10",
            "missing sample for version 11",
        ]

    def test_present_step_with_missing_sample_reports_only_the_sample(self) -> None:
        assert chain_gaps(oldest=10, current=11, step_versions={10}, sample_versions={10}) == [
            "missing sample for version 11"
        ]

    def test_sample_below_oldest_is_extra(self) -> None:
        assert chain_gaps(oldest=11, current=11, step_versions=set(), sample_versions={10, 11}) == [
            "extra sample for version 10"
        ]

    def test_oldest_above_current_reports_inversion(self) -> None:
        assert chain_gaps(oldest=12, current=11, step_versions=set(), sample_versions=set()) == [
            "oldest readable version 12 is above current version 11"
        ]


class TestUpgradeChain:
    def test_steps_run_in_order(self) -> None:
        calls: list[int] = []

        def _step(version: int) -> object:
            def run(payload: dict[str, object]) -> dict[str, object]:
                calls.append(version)
                return {**payload, "schema_version": f"native_exam_document_v{version + 1}"}

            return run

        payload = {"schema_version": "native_exam_document_v8"}
        upgraded = upgrade_native_exam_document_payload(
            payload, version=8, steps={8: _step(8), 9: _step(9)}, current=10
        )

        assert calls == [8, 9]
        assert upgraded["schema_version"] == "native_exam_document_v10"

    def test_gap_in_chain_raises(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            upgrade_native_exam_document_payload(
                {"schema_version": "native_exam_document_v8"},
                version=8,
                steps={9: lambda payload: payload},
                current=10,
            )
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_version_at_current_returns_payload_unchanged(self) -> None:
        payload = {"schema_version": "native_exam_document_v10"}
        assert (
            upgrade_native_exam_document_payload(payload, version=10, steps={}, current=10)
            is payload
        )


class TestVersionParser:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("native_exam_document_v10", 10),
            ("native_exam_document_v1", 1),
            ("xnative_exam_document_v10", None),
            ("native_exam_document_v10x", None),
            ("native_exam_document_v10 ", None),
            (" native_exam_document_v10", None),
            ("v10", None),
            ("native_exam_document_v", None),
            ("", None),
            (10, None),
            (None, None),
        ],
    )
    def test_version_parser(self, raw: object, expected: int | None) -> None:
        assert native_exam_document_version(raw) == expected


class TestReaderVersions:
    def test_current_version_parses(self) -> None:
        document = make_document(make_free_text_item())
        assert parse_native_exam_document(native_exam_document_json_bytes(document)) == document

    @pytest.mark.parametrize("version", [9, 11])
    def test_below_oldest_and_above_current_are_outdated(self, version: int) -> None:
        raw = f"native_exam_document_v{version}"
        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(_stored_payload_bytes(raw))
        assert exc_info.value.code is ErrorCode.DOCUMENT_SCHEMA_OUTDATED
        assert exc_info.value.details == {"schema_version": raw}

    @pytest.mark.parametrize(
        "raw",
        ["native_exam_document_v10x", "v10", "native_exam_document_v", 10],
    )
    def test_other_forms_are_outdated(self, raw: object) -> None:
        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(_stored_payload_bytes(raw))
        assert exc_info.value.code is ErrorCode.DOCUMENT_SCHEMA_OUTDATED
        assert exc_info.value.details == {"schema_version": raw}

    def test_missing_schema_version_stays_a_validation_error(self) -> None:
        payload = json.loads(
            native_exam_document_json_bytes(make_document(make_free_text_item())).decode("utf-8")
        )
        del payload["schema_version"]
        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(json.dumps(payload).encode("utf-8"))
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_readability_matches_oldest_to_current(self) -> None:
        assert is_readable_native_exam_document_version(10) is True
        assert is_readable_native_exam_document_version(9) is False
        assert is_readable_native_exam_document_version(11) is False
