"""Adversarial route-table coverage for the retired signed-in Exam Converter surface."""

from __future__ import annotations

from uuid import UUID

import pytest
from starlette.routing import BaseRoute, Match

from skriptoteket.web.router import router

_APP = "/api/v1/apps/documents.conversion_hub"
_PUBLIC_APP = "/api/v1/public/apps/documents.conversion_hub"
_JOB = UUID("37301f02-db48-40cd-9429-d0d23748d12c")
_SPA_FALLBACK_PATH = "/{full_path:path}"


def _full_matches(*, method: str, path: str) -> list[BaseRoute]:
    scope = {"type": "http", "method": method, "path": path, "root_path": ""}
    # The SPA history fallback matches every GET and answers 404 for /api paths, so it
    # is excluded: only API routes that actually own the path count.
    return [
        route
        for route in router.routes
        if getattr(route, "path", None) != _SPA_FALLBACK_PATH
        and route.matches(scope)[0] is Match.FULL
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", f"{_APP}/exam-converter/jobs/{_JOB}/artifacts/qti_package/save"),
        ("POST", f"{_APP}/exam-converter/conversions"),
        ("GET", f"{_APP}/exam-converter/jobs/{_JOB}/result"),
        ("GET", f"{_APP}/exam-converter/jobs/{_JOB}/artifacts"),
        ("GET", f"{_APP}/exam-converter/jobs/{_JOB}/artifacts/qti_package"),
        ("GET", f"{_APP}/exam-converter/jobs/{_JOB}/source-state"),
        ("POST", f"{_APP}/exam-converter/jobs/{_JOB}/replay"),
        ("GET", f"{_APP}/exam-converter/jobs/{_JOB}/correction-session"),
        ("PUT", f"{_APP}/exam-converter/jobs/{_JOB}/correction-session"),
        ("DELETE", f"{_APP}/exam-converter/jobs/{_JOB}/correction-session"),
        ("GET", f"{_APP}/exam-converter/jobs/{_JOB}/correction-session/intents"),
        ("PUT", f"{_APP}/exam-converter/jobs/{_JOB}/correction-session/intents"),
        ("DELETE", f"{_APP}/exam-converter/jobs/{_JOB}/correction-session/intents"),
    ],
)
def test_retired_signed_in_exam_converter_path_is_unrouted(method: str, path: str) -> None:
    assert _full_matches(method=method, path=path) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", f"{_APP}/routes"),
        ("POST", f"{_APP}/jobs"),
        ("GET", f"{_APP}/jobs/{_JOB}"),
        ("GET", f"{_APP}/jobs/{_JOB}/artifact"),
        ("POST", f"{_PUBLIC_APP}/exam-converter/jobs"),
    ],
)
def test_generic_and_public_exam_converter_routes_remain_registered(method: str, path: str) -> None:
    assert len(_full_matches(method=method, path=path)) == 1
