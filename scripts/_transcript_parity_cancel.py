"""Transcript parity cancel evidence helpers.

Domain purpose:
    Classify PR-0349 transcript cancel proof evidence from sanitized network
    records so retained artifacts distinguish local upload aborts from
    Sir Convert job cancel responses.

Relationships:
    Used by the PR-0349 Playwright proof harness and focused summary
    truthfulness tests.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypedDict

from scripts._transcript_parity_evidence import NetworkRecord

CancelPath = Literal["sir_convert_job_cancel", "upload_abort"]


class CancelPathEvidence(TypedDict):
    cancel_status: int | None
    cancel_payload: object | None
    cancel_path: CancelPath


def classify_cancel_path(records: Sequence[NetworkRecord]) -> CancelPathEvidence:
    cancel_record = next((record for record in records if _is_cancel_response(record)), None)
    if cancel_record is None:
        return {
            "cancel_status": None,
            "cancel_payload": None,
            "cancel_path": "upload_abort",
        }
    return {
        "cancel_status": cancel_record["status"],
        "cancel_payload": cancel_record["scrubbed_payload"],
        "cancel_path": "sir_convert_job_cancel",
    }


def _is_cancel_response(record: NetworkRecord) -> bool:
    path_without_query = record["path"].split("?", 1)[0]
    return record["method"] == "POST" and path_without_query.endswith("/cancel")
