"""Live API calls for the smart-seating semantics proof.

Each function parses one classroom-planner API response into the shape its
caller reads; the entrypoint in `live_st_27_03_smart_seating_semantics_check`
owns session setup, the run loop and the invariant checks.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import NotRequired, TypedDict

import requests
from pydantic import JsonValue, TypeAdapter

from scripts._smart_seating_semantics_support import (
    KEEP_APART_STUDENT_IDS,
    KEEP_NEAR_STUDENT_IDS,
    NEAR_TEACHER_STUDENT_IDS,
    SA24D_STUDENT_NAMES,
    TEMPLATE_PAYLOAD,
    WORKSPACE_PAYLOAD,
    TemplatePayload,
    WorkspacePayload,
    student_id,
)


class _TemplateRef(TypedDict):
    id: str
    name: NotRequired[JsonValue]


class _RosterResult(TypedDict):
    id: str
    name: str


class _DraftResult(TypedDict):
    id: str
    revision: int


class _ExportJob(TypedDict):
    job_id: str


class _ExportJobStatus(TypedDict):
    status: str
    error: NotRequired[JsonValue]


class _SmartRunResult(TypedDict):
    status: str
    used_history: bool
    message: str
    workspace: WorkspacePayload


_TEMPLATE_LIST = TypeAdapter(list[_TemplateRef])
_ROSTER_RESULT = TypeAdapter(_RosterResult)
_DRAFT_RESULT = TypeAdapter(_DraftResult)
_EXPORT_JOB = TypeAdapter(_ExportJob)
_EXPORT_JOB_STATUS = TypeAdapter(_ExportJobStatus)
_SMART_RUN_RESULT = TypeAdapter(_SmartRunResult)


def api_get(session: requests.Session, *, api_base_url: str, path: str) -> JsonValue:
    response = session.get(f"{api_base_url}{path}", timeout=30)
    response.raise_for_status()
    data: JsonValue = response.json()
    return data


def api_mutate(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    method: str,
    path: str,
    payload: Mapping[str, JsonValue] | None = None,
) -> JsonValue:
    response = session.request(
        method=method,
        url=f"{api_base_url}{path}",
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
        timeout=30,
    )
    response.raise_for_status()
    data: JsonValue = response.json() if response.content else {}
    return data


def create_roster(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    name: str,
) -> _RosterResult:
    return _ROSTER_RESULT.validate_python(
        api_mutate(
            session,
            api_base_url=api_base_url,
            csrf_token=csrf_token,
            method="POST",
            path="/api/v1/apps/classroom.group-seating-studio/rosters",
            payload={
                "name": name,
                "students": [
                    {"id": student_id(student_name), "display_name": student_name}
                    for student_name in SA24D_STUDENT_NAMES
                ],
            },
        )
    )


def get_g20_template(session: requests.Session, *, api_base_url: str) -> TemplatePayload:
    templates = _TEMPLATE_LIST.validate_python(
        api_get(
            session,
            api_base_url=api_base_url,
            path="/api/v1/apps/classroom.group-seating-studio/templates",
        )
    )
    matching_template = next(
        (template for template in templates if template.get("name") == "G20"),
        None,
    )
    if matching_template is None:
        raise AssertionError("Missing live G20 template.")
    template = TEMPLATE_PAYLOAD.validate_python(
        api_get(
            session,
            api_base_url=api_base_url,
            path=f"/api/v1/apps/classroom.group-seating-studio/templates/{matching_template['id']}",
        )
    )
    if len(template["seats"]) != 31:
        raise AssertionError("Live G20 template no longer matches the canonical 31-seat room.")
    return template


def create_seating_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
    template_id: str,
) -> _DraftResult:
    return _DRAFT_RESULT.validate_python(
        api_mutate(
            session,
            api_base_url=api_base_url,
            csrf_token=csrf_token,
            method="POST",
            path="/api/v1/apps/classroom.group-seating-studio/drafts/seating/new",
            payload={"roster_id": roster_id, "template_id": template_id},
        )
    )


def patch_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    draft_id: str,
    expected_revision: int,
    **fields: JsonValue,
) -> int:
    """Patch the draft and return the revision the response reports."""

    workspace = WORKSPACE_PAYLOAD.validate_python(
        api_mutate(
            session,
            api_base_url=api_base_url,
            csrf_token=csrf_token,
            method="PATCH",
            path=f"/api/v1/apps/classroom.group-seating-studio/drafts/{draft_id}",
            payload={"expected_revision": expected_revision, **fields},
        )
    )
    return workspace["draft"]["revision"]


def patch_smart_rules(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
    expected_revision: int,
) -> None:
    api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="PATCH",
        path=f"/api/v1/apps/classroom.group-seating-studio/rosters/{roster_id}/smart-rules",
        payload={
            "expected_revision": expected_revision,
            "seating_preferences": [
                {"student_id": student_id, "near_teacher": True}
                for student_id in sorted(NEAR_TEACHER_STUDENT_IDS)
            ],
            "relationship_rules": [
                {
                    "id": "apart-a",
                    "kind": "keep_apart",
                    "student_ids": list(KEEP_APART_STUDENT_IDS),
                },
                {
                    "id": "near-b",
                    "kind": "keep_near",
                    "student_ids": list(KEEP_NEAR_STUDENT_IDS),
                },
            ],
        },
    )


def create_export_checkpoint(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    draft_id: str,
) -> None:
    job = _EXPORT_JOB.validate_python(
        api_mutate(
            session,
            api_base_url=api_base_url,
            csrf_token=csrf_token,
            method="POST",
            path=f"/api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/exports/jobs",
            payload={
                "export_kind": "pdf",
                "layout_id": "pretty_brutalist_poster",
                "paper_size": "a3_landscape",
            },
        )
    )
    job_id = job["job_id"]
    for _ in range(90):
        status_payload = _EXPORT_JOB_STATUS.validate_python(
            api_get(
                session,
                api_base_url=api_base_url,
                path=f"/api/v1/apps/classroom.group-seating-studio/exports/jobs/{job_id}",
            )
        )
        if status_payload["status"] == "succeeded":
            return
        if status_payload["status"] == "failed":
            raise AssertionError(f"Seating export job failed: {status_payload.get('error')}")
        time.sleep(1)
    raise AssertionError("Timed out waiting for a live seating export checkpoint.")


def run_smart_seating(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    draft_id: str,
    expected_revision: int,
) -> _SmartRunResult:
    return _SMART_RUN_RESULT.validate_python(
        api_mutate(
            session,
            api_base_url=api_base_url,
            csrf_token=csrf_token,
            method="POST",
            path=f"/api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/smart-run",
            payload={"expected_revision": expected_revision},
        )
    )
